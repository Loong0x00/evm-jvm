// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {StockPageError,S2bClassError,S2bLinkError} from "./S2bTypes.sol";
import {S2bMetadataPage} from "./S2bMetadataPage.sol";

/// Append-only schema-4 linker and the schema-3-to-schema-4 reparse adapter.
contract S2bClassLinker {
    bytes32 private constant METADATA_MAGIC=keccak256("JVMEVM:S2B:LINK:METADATA:4");
    bytes32 private constant DCLASS=keccak256("JVMEVM:S2B:LINK:CLASS:4");
    bytes32 private constant OLD_MAGIC=keccak256("JVMEVM:S2A:METADATA:3");
    bytes32 private constant OLD_DCLASS=keccak256("JVMEVM:S2A:CLASS");
    bytes4 private constant ANALYZE_SELECTOR=bytes4(keccak256("analyze(bytes,address,bytes32,bytes32)"));
    bytes4 private constant CLASS_RECORD_SELECTOR=bytes4(keccak256("classRecord(bytes32)"));

    struct Record {address metadataPage;bytes32 metadataHash;}
    mapping(bytes32=>Record) private records;
    mapping(bytes32=>bytes32) private registrations;

    address public immutable analyzer;
    bytes32 public immutable analyzerCodeHash;
    bytes32 public immutable acceptedS2aParserHash;

    event ClassRegistered(bytes32 indexed classId,address indexed rawPage,address metadataPage,
        bytes32 metadataHash,uint16 methods,uint16 literals,uint16 calls);

    constructor(address analyzer_,bytes32 expectedAnalyzerHash_,bytes32 acceptedS2aParserHash_){
        bytes32 actual;assembly("memory-safe"){actual:=extcodehash(analyzer_)}
        if(analyzer_==address(0)||analyzer_.code.length==0||actual==bytes32(0)||actual!=expectedAnalyzerHash_)revert S2bLinkError(1);
        if(acceptedS2aParserHash_==bytes32(0))revert S2bLinkError(3);
        analyzer=analyzer_;analyzerCodeHash=actual;acceptedS2aParserHash=acceptedS2aParserHash_;
    }

    function classRecord(bytes32 classId) external view returns(address metadataPage,bytes32 metadataHash){
        Record storage r=records[classId];return(r.metadataPage,r.metadataHash);
    }

    function registerClass(address page,bytes32 expectedPageHash,bytes32 expectedPayloadHash)
      external returns(bytes32 classId,address metadataPage,bytes32 metadataHash,uint16 methods,uint16 literals,uint16 calls){
        _checkAnalyzer();
        return _registerClass(page,expectedPageHash,expectedPayloadHash);
    }

    function registerFromS2a(address oldParser,bytes32 oldClassId)
      external returns(bytes32 classId,address metadataPage,bytes32 metadataHash,uint16 methods,uint16 literals,uint16 calls){
        _checkAnalyzer();
        bytes32 oldParserHash;assembly("memory-safe"){oldParserHash:=extcodehash(oldParser)}
        if(oldParser==address(0)||oldParserHash!=acceptedS2aParserHash)revert S2bLinkError(3);
        (address oldMetadataPage,bytes32 oldMetadataHash)=_legacyRecord(oldParser,oldClassId);
        (address rawPage,bytes32 rawHash,bytes32 payloadHash)=_legacyHeader(oldMetadataPage,oldMetadataHash,oldParserHash,oldClassId);
        return _registerClass(rawPage,rawHash,payloadHash);
    }

    function _registerClass(address page,bytes32 pageHash,bytes32 payloadHash)
      private returns(bytes32 classId,address metadataPage,bytes32 metadataHash,uint16 methods,uint16 literals,uint16 calls){
        bytes memory raw=_page(page,pageHash,payloadHash);
        bytes32 key=keccak256(abi.encode(page,pageHash,payloadHash));
        classId=registrations[key];
        if(classId!=bytes32(0)){
            Record storage old=records[classId];
            if(old.metadataPage==address(0)||old.metadataHash==bytes32(0))revert S2bClassError(6,0);
            (methods,literals,calls)=_metadataPage(old.metadataPage,old.metadataHash,page,pageHash,payloadHash,uint32(raw.length));
            return(classId,old.metadataPage,old.metadataHash,methods,literals,calls);
        }
        bytes memory metadata;
        (metadata,methods,literals,calls)=_callAnalyzer(raw,page,pageHash,payloadHash);
        _validateMetadata(metadata,page,pageHash,payloadHash,uint32(raw.length),methods,literals,calls);
        try new S2bMetadataPage(metadata) returns(S2bMetadataPage made){metadataPage=address(made);}catch{revert S2bClassError(6,0);}
        assembly("memory-safe"){metadataHash:=extcodehash(metadataPage)}
        if(metadataHash==bytes32(0)||metadataPage.code.length!=metadata.length+1)revert S2bClassError(6,0);
        bytes32 linkerHash;assembly("memory-safe"){linkerHash:=extcodehash(address())}
        classId=keccak256(abi.encode(DCLASS,uint32(4),linkerHash,analyzerCodeHash,page,pageHash,payloadHash,metadataHash));
        Record storage existing=records[classId];
        if(classId==bytes32(0)||existing.metadataPage!=address(0)||existing.metadataHash!=bytes32(0))revert S2bClassError(6,0);
        records[classId]=Record(metadataPage,metadataHash);registrations[key]=classId;
        emit ClassRegistered(classId,page,metadataPage,metadataHash,methods,literals,calls);
    }

    // Calls the analyzer with no returndata output area. RETURNDATASIZE is bounded
    // and the canonical ABI head is checked before any dynamic allocation/copy.
    function _callAnalyzer(bytes memory raw,address page,bytes32 pageHash,bytes32 payloadHash)
      private view returns(bytes memory metadata,uint16 methods,uint16 literals,uint16 calls){
        bytes memory input=abi.encodeWithSelector(ANALYZE_SELECTOR,raw,page,pageHash,payloadHash);
        bool ok;uint256 size;
        address target=analyzer;
        assembly("memory-safe"){ok:=staticcall(gas(),target,add(input,0x20),mload(input),0,0) size:=returndatasize()}
        if(!ok){if(size!=0&&size<=256)_bubble(size);revert S2bLinkError(2);}
        if(size<160||size>8096)revert S2bLinkError(2);
        bytes memory head=new bytes(160);
        assembly("memory-safe"){returndatacopy(add(head,0x20),0,160)}
        uint256 offset=uint256(_word(head,0));uint256 mw=uint256(_word(head,1));uint256 lw=uint256(_word(head,2));uint256 cw=uint256(_word(head,3));uint256 n=uint256(_word(head,4));
        if(offset!=128||mw>type(uint16).max||lw>type(uint16).max||cw>type(uint16).max||n>7936)revert S2bLinkError(2);
        uint256 padded=(n+31)&~uint256(31);
        if(size!=160+padded)revert S2bLinkError(2);
        if((n&31)!=0){bytes32 last;assembly("memory-safe"){returndatacopy(0,add(160,mul(div(n,32),32)),32) last:=mload(0)}
            uint256 padding=32-(n&31);if((uint256(last)&((uint256(1)<<(padding*8))-1))!=0)revert S2bLinkError(2);
        }
        metadata=new bytes(n);assembly("memory-safe"){returndatacopy(add(metadata,0x20),160,n)}
        methods=uint16(mw);literals=uint16(lw);calls=uint16(cw);
    }

    function _validateMetadata(bytes memory metadata,address page,bytes32 pageHash,bytes32 payloadHash,
      uint32 rawLength,uint16 methods,uint16 literals,uint16 calls) private view {
        if(metadata.length!=256+uint256(methods)*160+uint256(literals)*8+uint256(calls)*16||metadata.length>7936)revert S2bLinkError(2);
        uint256 h1=uint256(_word(metadata,1));uint256 h5=uint256(_word(metadata,5));
        if(_word(metadata,0)!=METADATA_MAGIC||address(uint160(h1))!=page||h1>>176!=0||
           _word(metadata,2)!=pageHash||_word(metadata,3)!=payloadHash||_word(metadata,6)!=analyzerCodeHash||_word(metadata,7)!=bytes32(0))revert S2bLinkError(2);
        uint16 cpCount=uint16(h5>>32);
        if(uint32(h5)!=rawLength||cpCount<1||cpCount>512||uint16(h5>>48)!=methods||uint16(h5>>64)!=literals||uint16(h5>>80)!=calls||h5>>96!=0)revert S2bLinkError(2);
    }

    function _metadataPage(address metadataPage,bytes32 expectedHash,address rawPage,bytes32 rawHash,
      bytes32 payloadHash,uint32 rawLength) private view returns(uint16 methods,uint16 literals,uint16 calls){
        uint256 size;bytes32 actual;bytes32 first;
        assembly("memory-safe"){size:=extcodesize(metadataPage) actual:=extcodehash(metadataPage) extcodecopy(metadataPage,0,0,1) first:=mload(0)}
        if(size<257||size>7937||actual!=expectedHash||bytes1(first)!=0)revert S2bClassError(6,0);
        bytes memory header=new bytes(256);assembly("memory-safe"){extcodecopy(metadataPage,add(header,0x20),1,256)}
        uint256 h5=uint256(_word(header,5));methods=uint16(h5>>48);literals=uint16(h5>>64);calls=uint16(h5>>80);
        if(size!=1+256+uint256(methods)*160+uint256(literals)*8+uint256(calls)*16)revert S2bClassError(6,0);
        _validateMetadataHeader(header,rawPage,rawHash,payloadHash,rawLength,methods,literals,calls);
    }

    function _validateMetadataHeader(bytes memory header,address page,bytes32 pageHash,bytes32 payloadHash,
      uint32 rawLength,uint16 methods,uint16 literals,uint16 calls) private view {
        uint256 h1=uint256(_word(header,1));uint256 h5=uint256(_word(header,5));uint16 cpCount=uint16(h5>>32);
        if(_word(header,0)!=METADATA_MAGIC||address(uint160(h1))!=page||h1>>176!=0||_word(header,2)!=pageHash||
          _word(header,3)!=payloadHash||_word(header,6)!=analyzerCodeHash||_word(header,7)!=bytes32(0)||uint32(h5)!=rawLength||
          cpCount<1||cpCount>512||uint16(h5>>48)!=methods||uint16(h5>>64)!=literals||uint16(h5>>80)!=calls||h5>>96!=0)
          revert S2bClassError(6,0);
    }

    function _legacyRecord(address oldParser,bytes32 oldClassId) private view returns(address metadataPage,bytes32 metadataHash){
        bytes memory input=abi.encodeWithSelector(CLASS_RECORD_SELECTOR,oldClassId);bool ok;uint256 size;
        assembly("memory-safe"){ok:=staticcall(gas(),oldParser,add(input,0x20),mload(input),0,0) size:=returndatasize()}
        if(!ok||size!=64)revert S2bLinkError(4);
        bytes32 aw;assembly("memory-safe"){returndatacopy(0,0,64) aw:=mload(0) metadataHash:=mload(32)}
        if(uint256(aw)>>160!=0)revert S2bLinkError(4);metadataPage=address(uint160(uint256(aw)));
        if(metadataPage==address(0)||metadataHash==bytes32(0))revert S2bLinkError(4);
    }

    function _legacyHeader(address oldMetadataPage,bytes32 expectedHash,bytes32 oldParserHash,bytes32 oldClassId)
      private view returns(address rawPage,bytes32 rawHash,bytes32 payloadHash){
        uint256 size;bytes32 actual;bytes32 first;
        assembly("memory-safe"){size:=extcodesize(oldMetadataPage) actual:=extcodehash(oldMetadataPage) extcodecopy(oldMetadataPage,0,0,1) first:=mload(0)}
        if(size<193||size>8192||actual!=expectedHash||bytes1(first)!=0)revert S2bLinkError(4);
        bytes memory h=new bytes(192);assembly("memory-safe"){extcodecopy(oldMetadataPage,add(h,0x20),1,192)}
        uint256 h1=uint256(_word(h,1));uint256 h5=uint256(_word(h,5));rawPage=address(uint160(h1));
        uint32 rawLength=uint32(h5);uint16 cpCount=uint16(h5>>32);uint16 methods=uint16(h5>>48);uint16 literals=uint16(h5>>64);
        if(_word(h,0)!=OLD_MAGIC||rawPage==address(0)||h1>>176!=0||rawLength==0||rawLength>4096||cpCount<1||cpCount>512||methods>32||literals>256||h5>>80!=0||
          size!=1+192+uint256(methods)*128+uint256(literals)*8)revert S2bLinkError(5);
        rawHash=_word(h,2);payloadHash=_word(h,3);
        bytes32 computed=keccak256(abi.encode(OLD_DCLASS,uint32(3),oldParserHash,rawPage,rawHash,payloadHash,expectedHash));
        if(computed!=oldClassId)revert S2bLinkError(5);
    }

    function _page(address page,bytes32 expectedPageHash,bytes32 expectedPayloadHash) private view returns(bytes memory payload){
        uint256 size;bytes32 actualHash;bytes32 first;
        assembly("memory-safe"){size:=extcodesize(page) actualHash:=extcodehash(page) extcodecopy(page,0,0,1) first:=mload(0)}
        if(size<2||size>4097)revert StockPageError(1);if(bytes1(first)!=0)revert StockPageError(2);
        if(actualHash!=expectedPageHash)revert StockPageError(3);
        payload=new bytes(size-1);assembly("memory-safe"){extcodecopy(page,add(payload,0x20),1,sub(size,1))}
        if(keccak256(payload)!=expectedPayloadHash)revert StockPageError(4);
    }

    function _checkAnalyzer() private view {bytes32 actual;address target=analyzer;assembly("memory-safe"){actual:=extcodehash(target)}if(actual!=analyzerCodeHash)revert S2bLinkError(1);}
    function _word(bytes memory data,uint256 index) private pure returns(bytes32 out){assembly("memory-safe"){out:=mload(add(add(data,0x20),mul(index,0x20)))}}
    function _bubble(uint256 size) private pure {assembly("memory-safe"){returndatacopy(0,0,size) revert(0,size)}}
}
