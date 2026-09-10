package vfs0a

import (
	"encoding/binary"
	"testing"

	"github.com/ethereum/go-ethereum/common"
)

// vfs0aHarnessCheckpointView is a test-only structural reader. Production keeps
// checkpoints opaque and asks the EVM to validate/inspect them. This reader is
// deliberately limited to checking the frozen envelope, counters, and terminal
// VFS records returned by that EVM.
type vfs0aHarnessCheckpointView struct {
	Instance, Parent, Runtime, Artifact, Config, Machine, Seed, VFS common.Hash
	Epoch, TotalJvm, TotalInternal                                  uint64
	Lifecycle                                                       uint8
	Result                                                          int32
	InodeCount, DescriptorCount                                     uint32
	LogicalFileBytes                                                uint64
	Descriptors                                                     []vfs0aHarnessDescriptorView
}

type vfs0aHarnessDescriptorView struct {
	ID, Inode, Owner, BindPC uint32
	Flags, Phase             uint8
	Cursor                   uint64
	BindDepth                uint16
}

type vfs0aHarnessCursor struct {
	t *testing.T
	b []byte
	i int
}

func (c *vfs0aHarnessCursor) take(n int) []byte {
	c.t.Helper()
	if n < 0 || c.i < 0 || c.i > len(c.b) || n > len(c.b)-c.i {
		c.t.Fatalf("truncated test checkpoint at %d taking %d of %d", c.i, n, len(c.b))
	}
	out := c.b[c.i : c.i+n]
	c.i += n
	return out
}

func (c *vfs0aHarnessCursor) u8() uint8   { return c.take(1)[0] }
func (c *vfs0aHarnessCursor) u16() uint16 { return binary.BigEndian.Uint16(c.take(2)) }
func (c *vfs0aHarnessCursor) u32() uint32 { return binary.BigEndian.Uint32(c.take(4)) }
func (c *vfs0aHarnessCursor) u64() uint64 { return binary.BigEndian.Uint64(c.take(8)) }
func (c *vfs0aHarnessCursor) skip(n int)  { c.take(n) }

func vfs0aHarnessReadCheckpointView(t *testing.T, checkpoint []byte) vfs0aHarnessCheckpointView {
	t.Helper()
	if len(checkpoint) < 280 || string(checkpoint[:8]) != "JVMVF0A1" || binary.BigEndian.Uint32(checkpoint[8:12]) != 1 {
		t.Fatalf("invalid VFS0a checkpoint envelope: bytes=%d", len(checkpoint))
	}
	if int(binary.BigEndian.Uint32(checkpoint[276:280])) != len(checkpoint)-280 {
		t.Fatalf("VFS0a checkpoint machine length mismatch: bytes=%d", len(checkpoint))
	}
	view := vfs0aHarnessCheckpointView{
		Instance: common.BytesToHash(checkpoint[12:44]), Epoch: binary.BigEndian.Uint64(checkpoint[44:52]),
		Parent: common.BytesToHash(checkpoint[52:84]), Runtime: common.BytesToHash(checkpoint[84:116]),
		Artifact: common.BytesToHash(checkpoint[116:148]), Config: common.BytesToHash(checkpoint[148:180]),
		Machine: common.BytesToHash(checkpoint[180:212]), Seed: common.BytesToHash(checkpoint[212:244]),
		VFS: common.BytesToHash(checkpoint[244:276]),
	}
	c := &vfs0aHarnessCursor{t: t, b: checkpoint[280:]}
	if string(c.take(4)) != "VFA1" {
		t.Fatal("invalid VFS0a machine magic")
	}
	view.Lifecycle = c.u8()
	view.Result = int32(c.u32())
	c.skip(1 + 4) // Java kind/ref are checked through SliceResult.
	view.TotalJvm, view.TotalInternal = c.u64(), c.u64()
	c.skip(int(c.u16())) // entry class
	c.skip(int(c.u16())) // entry method
	for args := c.u8(); args != 0; args-- {
		c.skip(4)
	}
	for classes := c.u16(); classes != 0; classes-- {
		c.skip(2) // initialization state and initializer-started flag
		for statics := c.u16(); statics != 0; statics-- {
			c.skip(2 + 32)
		}
	}
	for frames := c.u16(); frames != 0; frames-- {
		c.skip(2 + 2 + 4 + 32 + 1 + 4)
		c.skip(int(c.u16()) * 32)
		locals := int(c.u16())
		c.skip((locals + 7) / 8)
		c.skip(locals * 32)
	}
	nextHandle := c.u32()
	c.skip(22) // arena counters after nextHandle through exception field slots
	for handle := uint32(1); handle <= nextHandle; handle++ {
		if got := c.u32(); got != handle {
			t.Fatalf("heap ordinal=%d want=%d", got, handle)
		}
		metadata := c.take(32)
		c.skip(2 + 1)
		count := int(c.u32())
		width := 8
		if metadata[0]&0x80 != 0 { // HEAP_OBJECT_MARKER = 1 << 255
			width = 32
		}
		c.skip(count * width)
	}
	c.skip(1 + 1 + 4 + 32)   // pending Java exception
	c.skip(int(c.u16()) * 8) // intern handle/hash pairs

	c.skip(4 + 4)
	view.InodeCount, view.DescriptorCount = c.u32(), c.u32()
	view.LogicalFileBytes = c.u64()
	for inode := uint32(0); inode < view.InodeCount; inode++ {
		c.skip(4 + 1 + 1 + 4)
		nameLen, dataLen := int(c.u8()), int(c.u32())
		c.skip(nameLen + dataLen)
	}
	view.Descriptors = make([]vfs0aHarnessDescriptorView, view.DescriptorCount)
	for i := range view.Descriptors {
		d := &view.Descriptors[i]
		d.ID, d.Inode, d.Owner = c.u32(), c.u32(), c.u32()
		d.Flags, d.Cursor, d.Phase = c.u8(), c.u64(), c.u8()
		d.BindDepth, d.BindPC = c.u16(), c.u32()
	}
	if c.i != len(c.b) {
		t.Fatalf("test checkpoint reader ended at %d of %d machine bytes", c.i, len(c.b))
	}
	return view
}
