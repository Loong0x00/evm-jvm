// Measurement-only MC-ZI0 preflight prototype. Not production.
pragma solidity ^0.8.30;
interface IAS0 {
    function read(uint32,uint32) external view returns(bytes memory);
    function isSealed() external view returns(bool);
    function contentCommitment() external view returns(bytes32);
    function declaredLength() external view returns(uint32);
}
contract ZI0Prototype {
    error Bad(uint256 code);
    bytes32 constant AS0_CODEHASH=hex"c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896";
    uint32 constant MAX_ENTRIES=512;
    uint32 constant MAX_NAME=256;
    uint32 constant MAX_EXTRA=1024;
    uint32 constant MAX_COMMENT=1024;
    address public immutable owner;
    constructor(){ owner=msg.sender; }
    function _u16(bytes memory b,uint p) pure internal returns(uint16){return uint16(uint8(b[p]))|(uint16(uint8(b[p+1]))<<8);}
    function _u32(bytes memory b,uint p) pure internal returns(uint32){return uint32(_u16(b,p))|(uint32(_u16(b,p+2))<<16);}
    function _part(IAS0 s,uint32 at,uint32 n) view internal returns(bytes memory out){
        if(n>4096) revert Bad(1); out=s.read(at,n); if(out.length!=n) revert Bad(2);
    }
    function _eq(bytes memory a,bytes memory b) pure internal returns(bool){
        if(a.length!=b.length)return false; for(uint i;i<a.length;i++)if(a[i]!=b[i])return false; return true;
    }
    function _extraOK(bytes memory b,uint start,uint n) pure internal returns(bool){
        uint q=start;uint end=start+n; while(q<end){if(q+4>end)return false;uint id=_u16(b,q);uint z=_u16(b,q+2);if(id==1||q+4+z>end)return false;q+=4+z;}return q==end;
    }
    function scan(address store,bytes32 assertedRoot) external view returns(bytes32 indexRoot,uint32 count,uint32 cdOffset,uint32 cdSize,uint32 eocdOffset){
        if(msg.sender!=owner)revert Bad(3); bytes32 ch; assembly{ch:=extcodehash(store)} if(ch!=AS0_CODEHASH)revert Bad(4);
        IAS0 s=IAS0(store); if(!s.isSealed()||assertedRoot==bytes32(0)||s.contentCommitment()!=assertedRoot)revert Bad(5);
        uint32 size=s.declaredLength(); if(size<22)revert Bad(6);
        uint32 tail=size>65557?65557:size; bytes memory t=new bytes(tail); uint32 done;
        while(done<tail){uint32 n=tail-done;if(n>4096)n=4096;bytes memory x=_part(s,size-tail+done,n);for(uint j;j<n;j++)t[done+j]=x[j];done+=n;}
        uint found; uint ep;
        for(uint p=0;p+22<=tail;p++) if(_u32(t,p)==0x06054b50 && uint(size-tail)+p+22+_u16(t,p+20)==size){
            uint16 disk=_u16(t,p+4);uint16 cddisk=_u16(t,p+6);uint16 nd=_u16(t,p+8);uint16 nt=_u16(t,p+10);uint32 cs=_u32(t,p+12);uint32 co=_u32(t,p+16);
            if(disk==0&&cddisk==0&&nd==nt&&uint(co)+cs==uint(size-tail)+p){found++;ep=p;}
        }
        if(found!=1)revert Bad(7); eocdOffset=uint32(uint(size-tail)+ep); count=_u16(t,ep+10);cdSize=_u32(t,ep+12);cdOffset=_u32(t,ep+16);
        if(count>MAX_ENTRIES||(count==0)!=(cdSize==0)||uint(cdOffset)+cdSize!=eocdOffset)revert Bad(8);
        bytes[] memory names=new bytes[](count); uint32 cursor=cdOffset;uint32 prevEnd;uint32 prevLocal;
        indexRoot=keccak256(abi.encode("MC-ZI0/prototype/v1",store,assertedRoot,size,eocdOffset,cdOffset,cdSize,count));
        for(uint32 i=0;i<count;i++){
            bytes memory h=_part(s,cursor,46);if(_u32(h,0)!=0x02014b50)revert Bad(10);
            uint16 flags=_u16(h,8);uint16 method=_u16(h,10);uint32 crc=_u32(h,16);uint32 comp=_u32(h,20);uint32 plain=_u32(h,24);uint16 nl=_u16(h,28);uint16 xl=_u16(h,30);uint16 cl=_u16(h,32);uint16 disk=_u16(h,34);uint32 local=_u32(h,42);
            if(nl==0||nl>MAX_NAME||xl>MAX_EXTRA||cl>MAX_COMMENT)revert Bad(11);if((flags&0xf7f1)!=0||(method==0&&(flags&6)!=0)||disk!=0||comp==type(uint32).max||plain==type(uint32).max||local==type(uint32).max)revert Bad(12);if((method!=0&&method!=8)||(method==0&&comp!=plain))revert Bad(13);
            uint32 rlen=uint32(46+nl+xl+cl);if(uint(cursor)+rlen>uint(cdOffset)+cdSize)revert Bad(14);bytes memory rec=_part(s,cursor,rlen);if(!_extraOK(rec,46+nl,xl))revert Bad(15);
            bytes memory name=new bytes(nl);for(uint j;j<nl;j++)name[j]=rec[46+j];for(uint j;j<i;j++)if(keccak256(names[j])==keccak256(name)&&_eq(names[j],name))revert Bad(16);names[i]=name;
            bytes memory lh=_part(s,local,30);if(_u32(lh,0)!=0x04034b50||_u16(lh,6)!=flags||_u16(lh,8)!=method)revert Bad(17);uint16 lnl=_u16(lh,26);uint16 lxl=_u16(lh,28);if(lnl!=nl||lxl>MAX_EXTRA)revert Bad(18);
            bytes memory lr=_part(s,local,uint32(30+lnl+lxl));if(!_extraOK(lr,30+lnl,lxl))revert Bad(19);bytes memory lname=new bytes(lnl);for(uint j;j<lnl;j++)lname[j]=lr[30+j];if(!_eq(name,lname))revert Bad(20);
            uint32 data=local+uint32(30+lnl+lxl);uint dend=uint(data)+comp;if(dend>cdOffset)revert Bad(21);uint32 rend=uint32(dend);
            if((flags&8)==0){if(_u32(lh,14)!=crc||_u32(lh,18)!=comp||_u32(lh,22)!=plain)revert Bad(22);}else{
                if(_u32(lh,14)!=0||_u32(lh,18)!=0||_u32(lh,22)!=0)revert Bad(23);bytes memory d=_part(s,uint32(dend),16);
                if(_u32(d,0)==0x08074b50&&_u32(d,4)==crc&&_u32(d,8)==comp&&_u32(d,12)==plain)rend+=16;
                else if(_u32(d,0)==crc&&_u32(d,4)==comp&&_u32(d,8)==plain)rend+=12;else revert Bad(24);
            }
            if(rend>cdOffset)revert Bad(27);
            if(i>0&&(local<=prevLocal||local<prevEnd))revert Bad(25);prevLocal=local;prevEnd=rend;
            indexRoot=keccak256(abi.encode(indexRoot,i,keccak256(name),nl,method,flags,crc,comp,plain,data,uint32(dend),local,rend));cursor+=rlen;
        }
        if(cursor!=cdOffset+cdSize)revert Bad(26);
    }
}
