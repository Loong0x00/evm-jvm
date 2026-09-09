// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

error StockPageError(uint256 code);
error S2bClassError(uint256 code, uint256 rawOffset);
error S2bMethodError(uint256 code, uint256 methodIndex);
error S2bBytecodeError(uint256 code, uint256 methodIndex, uint256 pc);
error S2bCallError(uint256 code, uint256 callerMethodIndex, uint256 pc);
error S2bLinkError(uint256 code);
