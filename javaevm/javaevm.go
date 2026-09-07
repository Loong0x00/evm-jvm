// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// The go-ethereum library is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// The go-ethereum library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with the go-ethereum library. If not, see <http://www.gnu.org/licenses/>.

// Package javaevm translates the deliberately tiny Java subset used by the M0 demo
// into EVM runtime bytecode and runs it with geth's EVM.
package javaevm

import (
	"encoding/binary"
	"fmt"

	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/core/vm/runtime"
)

// Program is EVM runtime bytecode for one selected Java method.
type Program struct {
	Code      []byte
	Arguments int
}

// Result is the signed Java int result and gas used by the actual EVM call.
type Result struct {
	Value   int32
	GasUsed uint64
}

// CompileClass selects methodName from a classfile and translates its Code
// attribute. M0 accepts only a static method with int arguments and int return,
// whose bytecode consists of iload, iadd, and ireturn.
func CompileClass(classfile []byte, methodName string) (Program, error) {
	method, err := findMethod(classfile, methodName)
	if err != nil {
		return Program{}, err
	}
	args, err := intMethodDescriptor(method.descriptor)
	if err != nil {
		return Program{}, fmt.Errorf("method %q: %w", methodName, err)
	}
	if method.access&0x0008 == 0 { // ACC_STATIC
		return Program{}, fmt.Errorf("method %q is not static", methodName)
	}
	if method.code == nil {
		return Program{}, fmt.Errorf("method %q has no Code attribute", methodName)
	}
	code, err := translate(method.code, args)
	if err != nil {
		return Program{}, fmt.Errorf("method %q: %w", methodName, err)
	}
	return Program{Code: code, Arguments: args}, nil
}

// Run executes p as EVM runtime bytecode. Each argument is ABI-like calldata:
// a 32-byte word containing its Java int32 value. No Java computation happens
// in the host process.
func Run(p Program, args []int32, gasLimit uint64) (Result, error) {
	if len(args) != p.Arguments {
		return Result{}, fmt.Errorf("method needs %d arguments, got %d", p.Arguments, len(args))
	}
	if gasLimit == 0 {
		return Result{}, fmt.Errorf("gas limit must be greater than zero")
	}
	input := make([]byte, 32*len(args))
	for i, arg := range args {
		binary.BigEndian.PutUint32(input[i*32+28:i*32+32], uint32(arg))
	}
	var gasUsed uint64
	cfg := &runtime.Config{GasLimit: gasLimit, EVMConfig: vm.Config{Tracer: &tracing.Hooks{
		OnTxEnd: func(receipt *types.Receipt, _ error) { gasUsed = receipt.GasUsed },
	}}}
	output, _, err := runtime.Execute(p.Code, input, cfg)
	result := Result{GasUsed: gasUsed}
	if err != nil {
		return result, fmt.Errorf("EVM execution failed: %w", err)
	}
	if len(output) != 32 {
		return result, fmt.Errorf("EVM returned %d bytes, want 32", len(output))
	}
	result.Value = int32(binary.BigEndian.Uint32(output[28:]))
	return result, nil
}

type selectedMethod struct {
	access     uint16
	descriptor string
	code       []byte
}

func findMethod(data []byte, wanted string) (selectedMethod, error) {
	r := classReader{data: data}
	if r.u4() != 0xcafebabe {
		return selectedMethod{}, r.errOr("not a Java classfile (missing CAFEBABE)")
	}
	r.u2() // minor version
	r.u2() // major version
	cpCount := int(r.u2())
	if r.err != nil || cpCount == 0 {
		return selectedMethod{}, r.errOr("invalid constant pool count")
	}
	utf8 := make([]string, cpCount)
	for i := 1; i < cpCount; i++ {
		tag := r.u1()
		switch tag {
		case 1: // CONSTANT_Utf8
			n := int(r.u2())
			utf8[i] = string(r.bytes(n))
		case 3, 4:
			r.skip(4)
		case 5, 6:
			r.skip(8)
			i++ // long/double consume two constant-pool slots
		case 7, 8, 16, 19, 20:
			r.skip(2)
		case 9, 10, 11, 12, 17, 18:
			r.skip(4)
		case 15:
			r.skip(3)
		default:
			return selectedMethod{}, fmt.Errorf("classfile: unsupported constant pool tag %d", tag)
		}
	}
	if r.err != nil {
		return selectedMethod{}, r.err
	}
	r.skip(6) // access_flags, this_class, super_class
	r.skip(2 * int(r.u2()))
	if err := skipMembers(&r); err != nil {
		return selectedMethod{}, err // fields
	}
	count := int(r.u2())
	var found *selectedMethod
	for i := 0; i < count; i++ {
		access := r.u2()
		name := cpString(utf8, r.u2())
		descriptor := cpString(utf8, r.u2())
		attrs := int(r.u2())
		var code []byte
		for j := 0; j < attrs; j++ {
			attrName := cpString(utf8, r.u2())
			attr := r.bytes(int(r.u4()))
			if r.err != nil {
				return selectedMethod{}, r.err
			}
			if attrName == "Code" {
				var err error
				code, err = codeBytes(attr)
				if err != nil {
					return selectedMethod{}, fmt.Errorf("classfile: invalid Code attribute for %q: %w", name, err)
				}
			}
		}
		if r.err != nil {
			return selectedMethod{}, r.err
		}
		if name == wanted {
			if found != nil {
				return selectedMethod{}, fmt.Errorf("classfile: method %q is overloaded; select an unambiguous name", wanted)
			}
			found = &selectedMethod{access: access, descriptor: descriptor, code: code}
		}
	}
	if r.err != nil {
		return selectedMethod{}, r.err
	}
	if err := skipAttributes(&r); err != nil {
		return selectedMethod{}, err // class attributes
	}
	if r.pos != len(data) {
		return selectedMethod{}, fmt.Errorf("classfile: trailing data at byte %d", r.pos)
	}
	if found == nil {
		return selectedMethod{}, fmt.Errorf("classfile: method %q not found", wanted)
	}
	return *found, nil
}

func skipMembers(r *classReader) error {
	count := int(r.u2())
	for i := 0; i < count; i++ {
		r.skip(6)
		attrs := int(r.u2())
		for j := 0; j < attrs; j++ {
			r.skip(2)
			r.skip(int(r.u4()))
		}
	}
	return r.err
}

func codeBytes(attr []byte) ([]byte, error) {
	r := classReader{data: attr}
	r.u2() // max_stack
	r.u2() // max_locals
	code := append([]byte(nil), r.bytes(int(r.u4()))...)
	r.skip(8 * int(r.u2())) // exception table
	if err := skipAttributes(&r); err != nil {
		return nil, err
	}
	if r.err != nil || r.pos != len(attr) {
		return nil, r.errOr("trailing or truncated Code attribute")
	}
	return code, nil
}

func skipAttributes(r *classReader) error {
	for n := int(r.u2()); n > 0; n-- {
		r.skip(2)
		r.skip(int(r.u4()))
	}
	return r.err
}

func intMethodDescriptor(desc string) (int, error) {
	if len(desc) < 3 || desc[0] != '(' {
		return 0, fmt.Errorf("invalid method descriptor %q", desc)
	}
	i := 1
	args := 0
	for i < len(desc) && desc[i] != ')' {
		if desc[i] != 'I' {
			return 0, fmt.Errorf("only int arguments are supported (descriptor %q)", desc)
		}
		args++
		i++
	}
	if i >= len(desc)-1 || desc[i] != ')' || desc[i+1:] != "I" {
		return 0, fmt.Errorf("only an int return is supported (descriptor %q)", desc)
	}
	return args, nil
}

func translate(java []byte, args int) ([]byte, error) {
	var evm []byte
	stack := 0
	returned := false
	for pc := 0; pc < len(java); pc++ {
		op := java[pc]
		switch {
		case op == 0x15: // iload index
			pc++
			if pc == len(java) {
				return nil, fmt.Errorf("truncated iload at bytecode offset %d", pc-1)
			}
			if err := emitLoad(&evm, int(java[pc]), args); err != nil {
				return nil, fmt.Errorf("bytecode offset %d: %w", pc-1, err)
			}
			stack++
		case op >= 0x1a && op <= 0x1d: // iload_0 through iload_3
			if err := emitLoad(&evm, int(op-0x1a), args); err != nil {
				return nil, fmt.Errorf("bytecode offset %d: %w", pc, err)
			}
			stack++
		case op == 0x60: // iadd
			if stack < 2 {
				return nil, fmt.Errorf("bytecode offset %d: iadd stack underflow", pc)
			}
			evm = append(evm, 0x01) // ADD
			emitMask(&evm)
			stack--
		case op == 0xac: // ireturn
			if stack != 1 {
				return nil, fmt.Errorf("bytecode offset %d: ireturn needs exactly one value", pc)
			}
			if pc != len(java)-1 {
				return nil, fmt.Errorf("bytecode offset %d: bytecode follows ireturn", pc)
			}
			evm = append(evm, 0x60, 0x00, 0x52, 0x60, 0x20, 0x60, 0x00, 0xf3) // MSTORE; RETURN(0, 32)
			returned = true
		default:
			return nil, fmt.Errorf("bytecode offset %d: unsupported opcode 0x%02x", pc, op)
		}
	}
	if !returned {
		return nil, fmt.Errorf("method has no ireturn")
	}
	return evm, nil
}

func emitLoad(evm *[]byte, local, args int) error {
	if local >= args {
		return fmt.Errorf("iload local %d is not an int argument", local)
	}
	emitPush(evm, uint64(local*32))
	*evm = append(*evm, 0x35) // CALLDATALOAD
	emitMask(evm)
	return nil
}

func emitMask(evm *[]byte) {
	*evm = append(*evm, 0x63, 0xff, 0xff, 0xff, 0xff, 0x16) // PUSH4 0xffffffff; AND
}

func emitPush(evm *[]byte, n uint64) {
	if n == 0 {
		*evm = append(*evm, 0x60, 0x00)
		return
	}
	width := 0
	for v := n; v > 0; v >>= 8 {
		width++
	}
	*evm = append(*evm, byte(0x5f+width))
	for shift := uint((width - 1) * 8); ; shift -= 8 {
		*evm = append(*evm, byte(n>>shift))
		if shift == 0 {
			break
		}
	}
}

type classReader struct {
	data []byte
	pos  int
	err  error
}

func (r *classReader) bytes(n int) []byte {
	if r.err != nil {
		return nil
	}
	if n < 0 || n > len(r.data)-r.pos {
		r.err = fmt.Errorf("classfile: truncated input at byte %d", r.pos)
		return nil
	}
	out := r.data[r.pos : r.pos+n]
	r.pos += n
	return out
}
func (r *classReader) u1() byte {
	b := r.bytes(1)
	if len(b) == 1 {
		return b[0]
	}
	return 0
}
func (r *classReader) u2() uint16 { return binary.BigEndian.Uint16(pad(r.bytes(2), 2)) }
func (r *classReader) u4() uint32 { return binary.BigEndian.Uint32(pad(r.bytes(4), 4)) }
func (r *classReader) skip(n int) { r.bytes(n) }
func (r *classReader) errOr(s string) error {
	if r.err != nil {
		return r.err
	}
	return fmt.Errorf("classfile: %s", s)
}

func pad(b []byte, n int) []byte {
	if len(b) == n {
		return b
	}
	return make([]byte, n)
}

func cpString(pool []string, index uint16) string {
	if int(index) >= len(pool) {
		return ""
	}
	return pool[index]
}
