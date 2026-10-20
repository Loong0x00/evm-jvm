// SPDX-License-Identifier: LGPL-3.0-or-later
pragma solidity 0.8.30;
// Diagnostic only: authenticated EVM class metadata, never guest execution/results.
interface IBoundCoordinator {
    function classBinding(uint8) external view returns(address,bytes memory,bytes32,uint32);
    function owner() external view returns(address);
    function finalIndexRoot() external view returns(bytes32);
    function packageRoot() external view returns(bytes32);
}
interface IBoundResource {
    function owner() external view returns(address);
    function phase() external view returns(uint8);
    function indexRoot() external view returns(bytes32);
    function plainSize() external view returns(uint32);
    function finalRoot() external view returns(bytes32);
    function read(uint32,uint32) external view returns(bytes memory);
}
contract BindingMethodInspector {
    address immutable coordinator;
    bytes32 immutable coordinatorHash;
    bytes32 immutable packageCommitment;
    bytes32 constant DI0_HASH=hex"946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37";
    struct Item {uint8 tag;uint256 a;uint256 b;}
    struct Result {bytes declaringClass;bytes methodName;bytes methodDescriptor;bytes newType;bytes constructorName;bytes constructorDescriptor;uint32 constructorPC;bytes32 resourceRoot;bytes32 rawKeccak;}
    constructor(address c,bytes32 hash,bytes32 root){coordinator=c;coordinatorHash=hash;packageCommitment=root;require(c.codehash==hash&&IBoundCoordinator(c).packageRoot()==root);}
    function n(bytes memory d,uint256 at,uint256 width) private pure returns(uint256 v){require(at<=d.length&&width<=d.length-at);for(uint256 i;i<width;++i)v=(v<<8)|uint8(d[at+i]);}
    function part(bytes memory d,uint256 at,uint256 len) private pure returns(bytes memory b){require(at<=d.length&&len<=d.length-at);b=new bytes(len);assembly("memory-safe"){mcopy(add(b,32),add(add(d,32),at),len)}}
    function utf(bytes memory d,Item[] memory pool,uint256 i) private pure returns(bytes memory){require(i!=0&&i<pool.length&&pool[i].tag==1);return part(d,pool[i].a,pool[i].b);}
    function cls(bytes memory d,Item[] memory pool,uint256 i) private pure returns(bytes memory){require(i!=0&&i<pool.length&&pool[i].tag==7);return utf(d,pool,pool[i].a);}
    function skipAttrs(bytes memory d,uint256 at,uint256 count) private pure returns(uint256){for(uint256 i;i<count;++i){uint256 len=n(d,at+2,4);require(at+6<=d.length&&len<=d.length-at-6);at+=6+len;}return at;}
    function width(bytes memory d,uint256 at,uint256 end) private pure returns(uint256 z){
        uint256 op=n(d,at,1);
        if(op<=0x0f||op>=0x1a&&op<=0x35||op>=0x3b&&op<=0x83||op>=0x85&&op<=0x98||op>=0xac&&op<=0xb1||op==0xbe||op==0xbf||op==0xc2||op==0xc3)z=1;
        else if(op==0x10||op==0x12||op>=0x15&&op<=0x19||op>=0x36&&op<=0x3a||op==0xa9||op==0xbc)z=2;
        else if(op==0x11||op==0x13||op==0x14||op==0x84||op>=0x99&&op<=0xa8||op>=0xb2&&op<=0xb8||op==0xbb||op==0xbd||op==0xc0||op==0xc1||op==0xc6||op==0xc7)z=3;
        else if(op==0xb9||op==0xba||op==0xc8||op==0xc9)z=5;
        else if(op==0xc5)z=4;
        else if(op==0xc4)z=n(d,at+1,1)==0x84?6:4;
        else revert("unsupported metadata scan opcode");
        require(at<=end&&z<=end-at);
    }
    function authenticatedRead(uint8 binding) private view returns(bytes memory raw,bytes32 root){
        require(coordinator.codehash==coordinatorHash);IBoundCoordinator c=IBoundCoordinator(coordinator);require(c.packageRoot()==packageCommitment);
        (address decoder,bytes memory name,bytes32 r,uint32 size)=c.classBinding(binding);
        require(keccak256(name)==keccak256(bytes("fd.class"))&&size>0&&size<=262144&&decoder.codehash==DI0_HASH);
        IBoundResource resource=IBoundResource(decoder);require(resource.owner()==c.owner()&&resource.phase()==4&&resource.indexRoot()==c.finalIndexRoot()&&resource.plainSize()==size&&resource.finalRoot()==r);
        raw=new bytes(size);for(uint32 at;at<size;){uint32 take=size-at;if(take>4096)take=4096;bytes memory b=resource.read(at,take);require(b.length==take);assembly("memory-safe"){mcopy(add(add(raw,32),at),add(b,32),take)}at+=take;}root=r;
    }
    function describe(uint8 binding,uint16 methodIndex,uint32 newPC) external view returns(Result memory result){
        bytes memory d;(d,result.resourceRoot)=authenticatedRead(binding);result.rawKeccak=keccak256(d);require(n(d,0,4)==0xcafebabe);
        uint256 count=n(d,8,2);Item[] memory pool=new Item[](count);uint256 at=10;
        for(uint256 i=1;i<count;++i){uint8 tag=uint8(n(d,at++,1));pool[i].tag=tag;
            if(tag==1){uint256 len=n(d,at,2);at+=2;require(len<=d.length-at);pool[i].a=at;pool[i].b=len;at+=len;}
            else if(tag==7||tag==8||tag==16||tag==19||tag==20){pool[i].a=n(d,at,2);at+=2;}
            else if(tag==9||tag==10||tag==11||tag==12||tag==18||tag==17){pool[i].a=n(d,at,2);pool[i].b=n(d,at+2,2);at+=4;}
            else if(tag==3||tag==4){n(d,at,4);at+=4;}
            else if(tag==5||tag==6){n(d,at,8);at+=8;++i;}
            else if(tag==15){n(d,at,3);at+=3;}
            else revert("constant tag");
        }
        result.declaringClass=cls(d,pool,n(d,at+2,2));require(keccak256(result.declaringClass)==keccak256(bytes("fd")));
        at+=6;uint256 interfaces=n(d,at,2);at+=2+2*interfaces;uint256 fields=n(d,at,2);at+=2;
        for(uint256 i;i<fields;++i){uint256 attributes=n(d,at+6,2);at=skipAttrs(d,at+8,attributes);}
        uint256 methods=n(d,at,2);at+=2;require(methodIndex<methods);
        for(uint256 i;i<methods;++i){uint256 methodAt=at;uint256 attrs=n(d,at+6,2);at+=8;
            if(i!=methodIndex){at=skipAttrs(d,at,attrs);continue;}
            result.methodName=utf(d,pool,n(d,methodAt+2,2));result.methodDescriptor=utf(d,pool,n(d,methodAt+4,2));
            for(uint256 a;a<attrs;++a){bytes memory attribute=utf(d,pool,n(d,at,2));uint256 attrLen=n(d,at+2,4);uint256 body=at+6;require(body<=d.length&&attrLen<=d.length-body);at=body+attrLen;
                if(keccak256(attribute)!=keccak256(bytes("Code")))continue;
                uint256 codeLen=n(d,body+4,4);uint256 start=body+8;require(codeLen<=attrLen-8&&newPC<codeLen&&n(d,start+newPC,1)==0xbb);result.newType=cls(d,pool,n(d,start+newPC+1,2));
                for(uint256 pc=newPC;pc<codeLen;){uint256 op=n(d,start+pc,1);uint256 step=width(d,start+pc,start+codeLen);
                    if(op==0xb7){uint256 ref=n(d,start+pc+1,2);require(ref<pool.length&&pool[ref].tag==10);Item memory nat=pool[pool[ref].b];require(nat.tag==12);bytes memory owner=cls(d,pool,pool[ref].a);bytes memory method=utf(d,pool,nat.a);
                        if(keccak256(owner)==keccak256(result.newType)&&keccak256(method)==keccak256(bytes("<init>"))){result.constructorName=method;result.constructorDescriptor=utf(d,pool,nat.b);result.constructorPC=uint32(pc);return result;}}
                    pc+=step;
                }
                revert("constructor not found in selected Code");
            }
            revert("selected method has no Code");
        }
        revert("selected method absent");
    }
}
