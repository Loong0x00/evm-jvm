// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

interface IDI0ZI0 {
    function lookup(bytes calldata rawName) external view returns (bool,uint32,bytes32);
    function owner() external view returns (address);
    function store() external view returns (address);
    function content() external view returns (bytes32);
    function phase() external view returns (uint8);
    function finalRoot() external view returns (bytes32);
}
interface IDI0AS0 { function read(uint32 offset,uint32 length) external view returns(bytes memory); }

/// Disposable DI0 preflight only. It deliberately has no production status.
contract DI0Inflate {
    error DI0Error(uint256 code);
    bytes32 constant ZI0_CODE = 0x0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77;
    bytes32 constant AS0_CODE = 0xc8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896;
    uint32 constant MAX_OUTPUT = 262144;
    uint16 constant MAX_UNITS = 128;
    uint8 constant COPY_UNIT = 32;
    uint32 constant OUTPUT_PAGE_SIZE = 8192;
    uint8 constant MAX_OUTPUT_PAGES = 32;

    address public owner;
    address public index;
    address public store;
    bytes32 public indexRoot;
    bytes32 public content;
    bytes32 public packedRecord;
    bytes32 public nameHash;
    bytes32 public binding;
    bytes32 public outputRolling;
    bytes32 public publicationRolling;
    bytes32 public finalRoot;
    uint32 public entryIndex;
    uint32 public dataStart;
    uint32 public compressedSize;
    uint32 public plainSize;
    uint32 public expectedCRC;
    uint32 public outputCount;
    uint32 public inputByte;
    uint32 public work;
    uint32 public crc = 0xffffffff;
    uint16 public pendingLength;
    uint16 public pendingDistance;
    uint8 public inputBit;
    uint8 public method;
    uint8 public phase; // 1 decoding, 2 verified, 3 publishing, 4 FINAL
    uint8 public blockMode; // 0 header, 1 stored bytes, 2 Huffman symbols
    bool public blockFinal;
    bool public fixedBlock;
    uint8 public publishedPages;
    uint8[288] private literalLengths;
    uint8[32] private distanceLengths;
    // Canonical dynamic tables are built once with each header and survive resumes.
    // Counts plus canonically ordered symbols avoid rebuilding memory arrays per token.
    uint16[16] private literalCounts;
    uint16[16] private distanceCounts;
    uint16[288] private literalSymbols;
    uint16[32] private distanceSymbols;
    mapping(uint256 => bytes32) private outputWords;
    address[32] private outputPages;
    bytes32[32] private outputPageHashes;
    bytes32[32] private outputPageCommitments;

    struct Reader { bytes raw; uint32 base; uint32 pos; uint8 bit; }

    constructor(address zi, bytes32 assertedRoot, bytes memory rawName) {
        if (msg.sender == address(0)) revert DI0Error(1);
        if (zi.codehash != ZI0_CODE) revert DI0Error(2);
        IDI0ZI0 z = IDI0ZI0(zi);
        if (z.phase() != 2 || z.finalRoot() != assertedRoot || assertedRoot == bytes32(0)) revert DI0Error(3);
        (bool found,uint32 number,bytes32 packed) = z.lookup(rawName);
        if (!found) revert DI0Error(4);
        uint256 p = uint256(packed);
        if ((p >> 195) != 0) revert DI0Error(5);
        uint32 start = uint32((p >> 50) & ((1 << 25)-1));
        uint32 comp = uint32((p >> 75) & ((1 << 25)-1));
        uint32 plain = uint32(p >> 100);
        uint32 wantCRC = uint32(p >> 132);
        uint8 meth = uint8((p >> 189) & 15);
        address as0 = z.store();
        if (as0.codehash != AS0_CODE || (meth != 0 && meth != 8) || plain > MAX_OUTPUT || uint64(start)+comp > type(uint32).max) revert DI0Error(5);
        if (meth == 0 && comp != plain) revert DI0Error(5);
        owner=msg.sender; index=zi; store=as0; indexRoot=assertedRoot; content=z.content();
        packedRecord=packed; nameHash=keccak256(rawName); entryIndex=number; dataStart=start;
        compressedSize=comp; plainSize=plain; expectedCRC=wantCRC; method=meth; phase=1;
        inputByte=start;
        binding=keccak256(abi.encode(keccak256("MC-DI0/binding/preflight/v1"),address(this),msg.sender,zi,ZI0_CODE,assertedRoot,as0,AS0_CODE,content,number,keccak256(rawName),packed,MAX_OUTPUT));
        outputRolling=keccak256(abi.encode(keccak256("MC-DI0/output/preflight/v1"),binding));
        if (meth == 0 && plain == 0) _complete();
    }

    function step(uint32 expectedWork,uint16 units) external {
        if (msg.sender != owner) revert DI0Error(1);
        if (phase != 1) revert DI0Error(6);
        if (expectedWork != work) revert DI0Error(7);
        if (units == 0 || units > MAX_UNITS) revert DI0Error(8);
        // One bounded AS0 read and one cursor save per call. The former version
        // fetched up to 4096 bytes and rebuilt decoder arrays for every action.
        Reader memory r = _reader();
        for (uint16 u=0; u<units && phase==1; u++) {
            if (pendingLength != 0 && method == 8 && blockMode == 2) _copyPending();
            else if (method == 0) _storedMethod(r);
            else if (blockMode == 0) _header(r);
            else if (blockMode == 1) _storedBlock(r);
            else _compressed(r);
            work++;
        }
        if (phase == 1) _save(r);
    }

    function publish(uint8 expectedPage,bytes32 expectedRolling,uint8 units) external {
        if (msg.sender != owner) revert DI0Error(1);
        if (phase != 2 && phase != 3) revert DI0Error(6);
        if (expectedPage != publishedPages || expectedRolling != publicationRolling) revert DI0Error(28);
        if (units != 1 || publishedPages >= MAX_OUTPUT_PAGES) revert DI0Error(29);
        uint32 start=uint32(publishedPages)*OUTPUT_PAGE_SIZE;
        if(start>=outputCount) revert DI0Error(29);
        uint32 n=outputCount-start; if(n>OUTPUT_PAGE_SIZE)n=OUTPUT_PAGE_SIZE;
        bytes memory raw=new bytes(n);
        for(uint32 i=0;i<n;i++)raw[i]=bytes1(_out(start+i));
        bytes memory init=bytes.concat(hex"61",bytes2(uint16(n+1)),hex"61000d5f3961",bytes2(uint16(n+1)),hex"5ff300",raw);
        address child; assembly ("memory-safe") { child := create(0,add(init,32),mload(init)) }
        if(child==address(0)) revert DI0Error(30);
        bytes32 ch=keccak256(bytes.concat(hex"00",raw)); if(child.codehash!=ch)revert DI0Error(31);
        bytes32 pc=keccak256(abi.encode(keccak256("MC-DI0/page/preflight/v2"),binding,publishedPages,n,keccak256(raw)));
        outputPages[publishedPages]=child;outputPageHashes[publishedPages]=ch;outputPageCommitments[publishedPages]=pc;
        publicationRolling=keccak256(abi.encode(keccak256("MC-DI0/published/preflight/v2"),publicationRolling,publishedPages,n,child,ch,pc));
        publishedPages++;
        if(uint32(publishedPages)*OUTPUT_PAGE_SIZE>=outputCount){phase=4;finalRoot=keccak256(abi.encode(keccak256("MC-DI0/final/preflight/v2"),binding,outputCount,expectedCRC,outputRolling,publishedPages,publicationRolling));}
        else phase=3;
    }

    function page(uint8 at) external view returns(address,bytes32,bytes32,uint32) {
        if(phase!=4)revert DI0Error(9);if(at>=publishedPages)revert DI0Error(32);
        uint32 n=outputCount-uint32(at)*OUTPUT_PAGE_SIZE;if(n>OUTPUT_PAGE_SIZE)n=OUTPUT_PAGE_SIZE;
        return(outputPages[at],outputPageHashes[at],outputPageCommitments[at],n);
    }
    function read(uint32 offset,uint32 length) external view returns(bytes memory out) {
        if (phase != 4) revert DI0Error(9);
        if (length > 4096 || uint64(offset)+length > outputCount) revert DI0Error(10);
        out=new bytes(length);uint32 done;
        while(done<length){uint32 absolute=offset+done;uint8 pi=uint8(absolute/OUTPUT_PAGE_SIZE);uint32 po=absolute%OUTPUT_PAGE_SIZE;
            address child=outputPages[pi];if(child.codehash!=outputPageHashes[pi])revert DI0Error(31);
            uint32 n=length-done;if(n>OUTPUT_PAGE_SIZE-po)n=OUTPUT_PAGE_SIZE-po;
            assembly { extcodecopy(child,add(add(out,32),done),add(po,1),n) } done+=n;
        }
    }

    function _reader() internal view returns(Reader memory r) {
        uint32 end=dataStart+compressedSize;
        if(inputByte>end) revert DI0Error(11);
        uint32 n=end-inputByte; if(n>4096)n=4096;
        r.raw=IDI0AS0(store).read(inputByte,n); r.base=inputByte; r.bit=inputBit;
    }
    function _bit(Reader memory r) internal view returns(uint256 v) {
        if(r.pos>=r.raw.length){
            uint32 absolute=r.base+r.pos;uint32 end=dataStart+compressedSize;
            if(r.bit!=0 || absolute>=end)revert DI0Error(11);
            uint32 n=end-absolute;if(n>4096)n=4096;
            r.raw=IDI0AS0(store).read(absolute,n);r.base=absolute;r.pos=0;
        }
        v=(uint8(r.raw[r.pos])>>r.bit)&1;
        r.bit++; if(r.bit==8){r.bit=0;r.pos++;}
    }
    function _bits(Reader memory r,uint8 n) internal view returns(uint256 v) {
        for(uint8 i=0;i<n;i++) v|=_bit(r)<<i;
    }
    function _align(Reader memory r) internal pure { if(r.bit!=0){r.bit=0;r.pos++;} }
    function _save(Reader memory r) internal { inputByte=r.base+r.pos; inputBit=r.bit; }

    function _storedMethod(Reader memory r) internal {
        uint32 left=plainSize-outputCount; uint32 n=left>COPY_UNIT?COPY_UNIT:left;
        for(uint32 i=0;i<n;i++) _emit(uint8(_bits(r,8)));
        if(outputCount==plainSize) {
            if(r.base+r.pos != dataStart+compressedSize || r.bit!=0) revert DI0Error(12);
            inputByte=r.base+r.pos; inputBit=0; _complete();
        } else _save(r);
    }
    function _header(Reader memory r) internal {
        blockFinal=_bit(r)!=0; uint256 typ=_bits(r,2);
        if(typ==3) revert DI0Error(13);
        if(typ==0){
            fixedBlock=false;
            _align(r); uint16 len=uint16(_bits(r,16)); uint16 nlen=uint16(_bits(r,16));
            if(uint16(~nlen)!=len) revert DI0Error(14);
            pendingLength=len; blockMode=1;
            if(len==0) _endStored(r);
        } else if(typ==1) { fixedBlock=true; blockMode=2; }
        else { fixedBlock=false; _dynamic(r); blockMode=2; }
    }
    function _storedBlock(Reader memory r) internal {
        uint16 n=pendingLength>COPY_UNIT?COPY_UNIT:pendingLength;
        for(uint16 i=0;i<n;i++) _emit(uint8(_bits(r,8)));
        pendingLength-=n; if(pendingLength==0) _endStored(r);
    }
    function _endStored(Reader memory r) internal {
        if(blockFinal) _finishDeflate(r); else blockMode=0;
    }
    function _compressed(Reader memory r) internal {
        uint16 sym=_decode(r,false);
        if(sym<256){_emit(uint8(sym));return;}
        if(sym==256){if(blockFinal)_finishDeflate(r);else blockMode=0;return;}
        if(sym>285) revert DI0Error(15);
        (uint16 base,uint8 extra)=_length(sym);
        uint16 length=base+uint16(_bits(r,extra));
        uint16 dsym=_decode(r,true); if(dsym>29) revert DI0Error(16);
        (uint16 dbase,uint8 de)=_distance(dsym);
        uint16 dist=dbase+uint16(_bits(r,de));
        if(dist==0 || dist>32768 || dist>outputCount) revert DI0Error(17);
        pendingLength=length; pendingDistance=dist;
    }
    function _copyPending() internal {
        uint16 n=pendingLength>COPY_UNIT?COPY_UNIT:pendingLength;
        for(uint16 i=0;i<n;i++) _emit(_out(outputCount-pendingDistance));
        pendingLength-=n; if(pendingLength==0)pendingDistance=0;
    }

    function _dynamic(Reader memory r) internal {
        uint16 hlit=uint16(_bits(r,5))+257; uint16 hdist=uint16(_bits(r,5))+1; uint8 hclen=uint8(_bits(r,4))+4;
        if(hlit>286 || hdist>30) revert DI0Error(27); // explicit Java8-compatible header-count profile
        uint8[19] memory cl; uint8[19] memory order=[uint8(16),17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15];
        for(uint8 i=0;i<hclen;i++)cl[order[i]]=uint8(_bits(r,3));
        uint16[16] memory cc; uint16[16] memory next; uint16[19] memory cs; uint16 used;
        for(uint16 i=0;i<19;i++){uint8 l=cl[i];if(l>15)revert DI0Error(20);if(l!=0){cc[l]++;used++;}}
        if(used==0)revert DI0Error(20); int32 left=1;
        for(uint8 l=1;l<=15;l++){left=left*2-int32(uint32(cc[l]));if(left<0)revert DI0Error(20);}
        if(left!=0)revert DI0Error(21);
        for(uint8 l=1;l<15;l++)next[l+1]=next[l]+cc[l];
        for(uint16 i=0;i<19;i++){uint8 l=cl[i];if(l!=0)cs[next[l]++]=i;}
        uint8[] memory all=new uint8[](uint256(hlit)+hdist); uint256 at;
        while(at<all.length){
            uint16 s=_decodeCL(r,cc,cs);
            if(s<=15){all[at++]=uint8(s);}
            else if(s==16){
                if(at==0)revert DI0Error(18); uint256 n=_bits(r,2)+3; if(at+n>all.length)revert DI0Error(18);
                uint8 prev=all[at-1]; while(n>0){all[at++]=prev;n--;}
            } else if(s==17){uint256 n=_bits(r,3)+3;if(at+n>all.length)revert DI0Error(18);at+=n;}
            else if(s==18){uint256 n=_bits(r,7)+11;if(at+n>all.length)revert DI0Error(18);at+=n;}
            else revert DI0Error(18);
        }
        for(uint16 i=0;i<288;i++)literalLengths[i]=i<hlit?all[i]:0;
        for(uint16 i=0;i<32;i++)distanceLengths[i]=i<hdist?all[uint256(hlit)+i]:0;
        if(literalLengths[256]==0)revert DI0Error(19);
        _buildStored(false); _buildStored(true);
    }

    function _buildStored(bool dist) internal {
        uint16[16] memory count; uint16[16] memory next; uint16 used; uint8 onlyLen;
        uint16 n=dist?32:288;
        for(uint16 i=0;i<n;i++){uint8 l=dist?distanceLengths[i]:literalLengths[i];if(l>15)revert DI0Error(20);if(l!=0){count[l]++;used++;onlyLen=l;}}
        if(used==0){
            if(!dist)revert DI0Error(21);
            for(uint8 l=0;l<16;l++)distanceCounts[l]=0;
            return;
        }
        int32 left=1;
        for(uint8 l=1;l<=15;l++){left=left*2-int32(uint32(count[l]));if(left<0)revert DI0Error(20);}
        if(left!=0 && !(used==1 && onlyLen==1))revert DI0Error(21);
        for(uint8 l=1;l<15;l++)next[l+1]=next[l]+count[l];
        for(uint16 i=0;i<n;i++){
            uint8 l=dist?distanceLengths[i]:literalLengths[i];
            if(l!=0){uint16 at=next[l]++;if(dist)distanceSymbols[at]=i;else literalSymbols[at]=i;}
        }
        for(uint8 l=0;l<16;l++){if(dist)distanceCounts[l]=count[l];else literalCounts[l]=count[l];}
    }
    function _decodeCL(Reader memory r,uint16[16] memory count,uint16[19] memory symbols) internal view returns(uint16){
        uint32 code;uint32 first;uint16 idx;
        for(uint8 l=1;l<=15;l++){
            code|=uint32(_bit(r));uint16 c=count[l];
            if(code>=first && code<first+c)return symbols[uint256(idx)+code-first];
            idx+=c;first=(first+c)<<1;code<<=1;
        }
        revert DI0Error(22);
    }
    function _decode(Reader memory r,bool dist) internal view returns(uint16){
        if(fixedBlock)return _decodeFixed(r,dist);
        uint32 code;uint32 first;uint16 idx;
        for(uint8 l=1;l<=15;l++){
            code|=uint32(_bit(r));uint16 c=dist?distanceCounts[l]:literalCounts[l];
            if(code>=first && code<first+c){uint256 at=uint256(idx)+code-first;return dist?distanceSymbols[at]:literalSymbols[at];}
            idx+=c;first=(first+c)<<1;code<<=1;
        }
        revert DI0Error(22);
    }
    function _decodeFixed(Reader memory r,bool dist) internal view returns(uint16){
        uint32 code;
        for(uint8 l=1;l<=9;l++){
            code|=uint32(_bit(r));
            if(dist && l==5)return uint16(code);
            if(!dist && l==7 && code<24)return uint16(256+code);
            if(!dist && l==8 && code>=48 && code<200){uint16 rank=uint16(code-48);return rank<144?rank:uint16(280+rank-144);}
            if(!dist && l==9 && code>=400 && code<512)return uint16(144+code-400);
            code<<=1;
        }
        revert DI0Error(22);
    }

    function _finishDeflate(Reader memory r) internal {
        uint32 end=dataStart+compressedSize; uint32 abs=r.base+r.pos;
        if(r.bit==0){if(abs!=end)revert DI0Error(23);}
        else {
            if(abs>=end || abs+1!=end)revert DI0Error(23);
            r.pos++;r.bit=0;
        }
        inputByte=end;inputBit=0;_complete();
    }
    function _complete() internal {
        if(outputCount!=plainSize)revert DI0Error(24);
        if((crc^0xffffffff)!=expectedCRC)revert DI0Error(25);
        phase=2;
        publicationRolling=keccak256(abi.encode(keccak256("MC-DI0/publication/preflight/v2"),binding,outputCount,expectedCRC,outputRolling,OUTPUT_PAGE_SIZE));
        if(outputCount==0){phase=4;finalRoot=keccak256(abi.encode(keccak256("MC-DI0/final/preflight/v2"),binding,outputCount,expectedCRC,outputRolling,uint8(0),publicationRolling));}
    }
    function _emit(uint8 b) internal {
        if(outputCount>=plainSize || outputCount>=MAX_OUTPUT)revert DI0Error(26);
        uint256 wi=outputCount>>5;uint256 sh=(31-(outputCount&31))*8;
        outputWords[wi]=bytes32(uint256(outputWords[wi])|(uint256(b)<<sh));
        uint32 c=crc^uint32(b);for(uint8 i=0;i<8;i++)c=(c&1)!=0?(c>>1)^0xedb88320:c>>1;crc=c;
        outputRolling=keccak256(abi.encode(keccak256("MC-DI0/byte/preflight/v1"),outputRolling,outputCount,b));
        outputCount++;
    }
    function _out(uint32 at) internal view returns(uint8){return uint8(uint256(outputWords[at>>5])>>((31-(at&31))*8));}
    function _length(uint16 s) internal pure returns(uint16 b,uint8 e){
        if(s<=264)return(uint16(s-254),0);if(s<=268)return(uint16(11+(s-265)*2),1);if(s<=272)return(uint16(19+(s-269)*4),2);
        if(s<=276)return(uint16(35+(s-273)*8),3);if(s<=280)return(uint16(67+(s-277)*16),4);if(s<=284)return(uint16(131+(s-281)*32),5);return(258,0);
    }
    function _distance(uint16 s) internal pure returns(uint16 b,uint8 e){
        if(s<=3)return(uint16(s+1),0);e=uint8(s/2-1);b=uint16((2+(s&1))<<e)+1;
    }
}
