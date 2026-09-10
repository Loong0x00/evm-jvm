// DISPOSABLE measurement-only MC-ZI0 persistent-index preflight. Not production.
pragma solidity ^0.8.30;

interface IAS0 {
    function read(uint32,uint32) external view returns(bytes memory);
    function isSealed() external view returns(bool);
    function contentCommitment() external view returns(bytes32);
    function declaredLength() external view returns(uint32);
}

contract ZI0Persistent {
    error ZI0Error(uint256 code);
    bytes32 constant AS0_CODEHASH=hex"c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896";
    uint32 constant MAX_ENTRIES=32768;
    uint32 constant MAX_CD=4194304;
    uint16 constant MAX_NAME=256;
    uint16 constant MAX_EXTRA=1024;
    uint16 constant MAX_COMMENT=1024;
    bytes32 constant D0=keccak256("MC-ZI0/index/v1");
    bytes32 constant DE=keccak256("MC-ZI0/entry/v1");

    address public owner;
    address public store;
    bytes32 public content;
    uint32 public length;
    uint8 public phase; // 0=bound, 1=STAGING, 2=FINAL
    uint32 public eocd;
    uint32 public cdOffset;
    uint32 public cdSize;
    uint32 public count;
    uint32 public nextEntry;
    uint32 public cdCursor;
    uint32 private prevLocal;
    uint32 private prevEnd;
    bytes32 public rolling; // staging diagnostic, never FINAL authority
    bytes32 public finalRoot; // zero until finish succeeds
    mapping(uint32=>uint256) private records;
    mapping(bytes32=>uint32) private nameIndex; // index+1

    constructor(address sealedAS0,bytes32 assertedContent) {
        owner=msg.sender; store=sealedAS0; content=assertedContent;
        _binding(); length=IAS0(store).declaredLength();
        if(length==0||length>33554432) revert ZI0Error(3);
    }
    function _binding() view internal {
        bytes32 ch; address s=store; assembly{ch:=extcodehash(s)}
        if(ch!=AS0_CODEHASH) revert ZI0Error(2);
        IAS0 a=IAS0(s);
        if(content==bytes32(0)||!a.isSealed()||a.contentCommitment()!=content) revert ZI0Error(3);
    }
    function _u16(bytes memory b,uint p) pure internal returns(uint16){return uint16(uint8(b[p]))|(uint16(uint8(b[p+1]))<<8);}
    function _u32(bytes memory b,uint p) pure internal returns(uint32){return uint32(_u16(b,p))|(uint32(_u16(b,p+2))<<16);}
    function _part(uint32 at,uint32 n) view internal returns(bytes memory out){
        if(n>4096||uint(at)+n>length) revert ZI0Error(16);
        out=IAS0(store).read(at,n); if(out.length!=n) revert ZI0Error(3);
    }
    function _eq(bytes memory a,bytes memory b) pure internal returns(bool){
        if(a.length!=b.length)return false; for(uint i;i<a.length;i++)if(a[i]!=b[i])return false; return true;
    }
    function _extraOK(bytes memory b,uint start,uint n) pure internal returns(bool){
        uint q=start;uint end=start+n;while(q<end){if(q+4>end)return false;uint id=_u16(b,q);uint z=_u16(b,q+2);if(id==1||q+4+z>end)return false;q+=4+z;}return q==end;
    }
    function discover() external {
        if(msg.sender!=owner)revert ZI0Error(1);if(phase!=0)revert ZI0Error(4);_binding();
        uint32 size=length;if(size<22)revert ZI0Error(5);uint32 tail=size>65557?65557:size;
        bytes memory t=new bytes(tail);uint32 done;
        while(done<tail){uint32 n=tail-done;if(n>4096)n=4096;bytes memory x=_part(size-tail+done,n);for(uint j;j<n;j++)t[done+j]=x[j];done+=n;}
        uint found;uint ep;
        for(uint p=0;p+22<=tail;p++)if(_u32(t,p)==0x06054b50&&uint(size-tail)+p+22+_u16(t,p+20)==size){
            uint16 disk=_u16(t,p+4);uint16 cddisk=_u16(t,p+6);uint16 nd=_u16(t,p+8);uint16 nt=_u16(t,p+10);uint32 cs=_u32(t,p+12);uint32 co=_u32(t,p+16);
            if(disk==0&&cddisk==0&&nd==nt&&uint(co)+cs==uint(size-tail)+p){found++;ep=p;}
        }
        if(found!=1)revert ZI0Error(6);uint32 eo=uint32(uint(size-tail)+ep);uint32 co=_u32(t,ep+16);uint32 cs=_u32(t,ep+12);uint32 ct=_u16(t,ep+10);
        if(ct>MAX_ENTRIES||cs>MAX_CD||(ct==0)!=(cs==0)||uint(co)+cs!=eo)revert ZI0Error(7);
        // Policy: reject a ZIP64 locator signature only at the sole structural prelude
        // position of an empty classic archive. Never scan arbitrary names/payloads.
        if(ct==0&&eo>=20){bytes memory q=_part(eo-20,4);if(_u32(q,0)==0x07064b50)revert ZI0Error(9);}
        eocd=eo;cdOffset=co;cdSize=cs;count=ct;cdCursor=co;
        rolling=keccak256(abi.encode(D0,address(this),owner,store,AS0_CODEHASH,content,length,eo,co,cs,ct));phase=1;
    }
    function _name(uint256 packed) view internal returns(bytes memory n){
        uint32 at=uint32(packed&0x1ffffff);uint16 nl=uint16((packed>>164)&0x1ff);n=_part(at,nl);
    }
    function scan(uint32 expectedEntry,uint32 expectedCursor,bytes32 expectedRolling,uint16 maxEntries) external {
        if(msg.sender!=owner)revert ZI0Error(1);if(phase!=1)revert ZI0Error(4);_binding();
        if(expectedEntry!=nextEntry||expectedCursor!=cdCursor||expectedRolling!=rolling)revert ZI0Error(10);
        if(maxEntries==0||maxEntries>64)revert ZI0Error(11);
        uint32 stop=nextEntry+maxEntries;if(stop>count)stop=count;uint32 cursor=cdCursor;uint32 pl=prevLocal;uint32 pe=prevEnd;bytes32 rr=rolling;
        for(uint32 i=nextEntry;i<stop;i++){
            bytes memory h=_part(cursor,46);if(_u32(h,0)!=0x02014b50)revert ZI0Error(12);
            uint16 flags=_u16(h,8);uint16 method=_u16(h,10);uint32 crc=_u32(h,16);uint32 comp=_u32(h,20);uint32 plain=_u32(h,24);uint16 nl=_u16(h,28);uint16 xl=_u16(h,30);uint16 cl=_u16(h,32);uint16 disk=_u16(h,34);uint32 local=_u32(h,42);
            if(nl==0||nl>MAX_NAME||xl>MAX_EXTRA||cl>MAX_COMMENT)revert ZI0Error(13);
            if((flags&0xf7f1)!=0||(method==0&&(flags&6)!=0)||disk!=0||comp==type(uint32).max||plain==type(uint32).max||local==type(uint32).max)revert ZI0Error(14);
            if((method!=0&&method!=8)||(method==0&&comp!=plain))revert ZI0Error(15);
            uint32 rlen=uint32(46+nl+xl+cl);if(uint(cursor)+rlen>uint(cdOffset)+cdSize)revert ZI0Error(16);bytes memory rec=_part(cursor,rlen);if(!_extraOK(rec,46+nl,xl))revert ZI0Error(17);
            bytes memory name=new bytes(nl);for(uint j;j<nl;j++)name[j]=rec[46+j];bytes32 nh=keccak256(name);uint32 occupied=nameIndex[nh];
            if(occupied!=0){bytes memory old=_name(records[occupied-1]);if(_eq(old,name))revert ZI0Error(18);revert ZI0Error(19);}
            bytes memory lh=_part(local,30);if(_u32(lh,0)!=0x04034b50||_u16(lh,6)!=flags||_u16(lh,8)!=method)revert ZI0Error(20);uint16 lnl=_u16(lh,26);uint16 lxl=_u16(lh,28);if(lnl!=nl||lxl>MAX_EXTRA)revert ZI0Error(21);
            bytes memory lr=_part(local,uint32(30+lnl+lxl));if(!_extraOK(lr,30+lnl,lxl))revert ZI0Error(22);bytes memory lname=new bytes(lnl);for(uint j;j<lnl;j++)lname[j]=lr[30+j];if(!_eq(name,lname))revert ZI0Error(22);
            uint32 data=local+uint32(30+lnl+lxl);uint dend=uint(data)+comp;if(dend>cdOffset)revert ZI0Error(23);uint32 rend=uint32(dend);uint8 desc;
            if((flags&8)==0){if(_u32(lh,14)!=crc||_u32(lh,18)!=comp||_u32(lh,22)!=plain)revert ZI0Error(24);}
            else{if(_u32(lh,14)!=0||_u32(lh,18)!=0||_u32(lh,22)!=0)revert ZI0Error(24);bytes memory d=_part(uint32(dend),16);if(_u32(d,0)==0x08074b50&&_u32(d,4)==crc&&_u32(d,8)==comp&&_u32(d,12)==plain){rend+=16;desc=2;}else if(_u32(d,0)==crc&&_u32(d,4)==comp&&_u32(d,8)==plain){rend+=12;desc=1;}else revert ZI0Error(25);}
            if(rend>cdOffset)revert ZI0Error(26);if(i>0&&(local<=pl||local<pe))revert ZI0Error(27);pl=local;pe=rend;
            uint32 namePos=cursor+46;if(namePos>=33554432||local>=33554432||data>=33554432||comp>=33554432)revert ZI0Error(14);
            uint256 packed=uint256(namePos)|(uint256(local)<<25)|(uint256(data)<<50)|(uint256(comp)<<75)|(uint256(plain)<<100)|(uint256(crc)<<132)|(uint256(nl)<<164)|(uint256(flags)<<173)|(uint256(method)<<189)|(uint256(desc)<<193);
            records[i]=packed;nameIndex[nh]=i+1;
            rr=keccak256(abi.encode(DE,rr,i,nh,nl,flags,method,crc,comp,plain,local,data,uint32(dend),rend,cursor+rlen));cursor+=rlen;
        }
        nextEntry=stop;cdCursor=cursor;prevLocal=pl;prevEnd=pe;rolling=rr;
    }
    function finish(uint32 expectedCount,uint32 expectedCursor,bytes32 expectedRolling) external {
        if(msg.sender!=owner)revert ZI0Error(1);if(phase!=1)revert ZI0Error(4);_binding();
        if(expectedCount!=count||nextEntry!=count||expectedCursor!=cdCursor||cdCursor!=cdOffset+cdSize||expectedRolling!=rolling)revert ZI0Error(29);
        finalRoot=rolling;phase=2;
    }
    function entry(uint32 index) external view returns(bytes memory rawName,bytes32 packedRecord){
        _binding();if(phase!=2)revert ZI0Error(30);if(index>=count)revert ZI0Error(31);uint256 p=records[index];return(_name(p),bytes32(p));
    }
    function lookup(bytes calldata rawName) external view returns(bool found,uint32 index,bytes32 packedRecord){
        _binding();if(phase!=2)revert ZI0Error(30);if(rawName.length==0||rawName.length>MAX_NAME)revert ZI0Error(32);uint32 x=nameIndex[keccak256(rawName)];if(x==0)return(false,0,bytes32(0));uint256 p=records[x-1];if(!_eq(_name(p),rawName))revert ZI0Error(19);return(true,x-1,bytes32(p));
    }
}
