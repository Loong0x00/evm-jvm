# Function interface link/apply slice (P42 -> P43)

Scope is one append-only Java 8 bootstrap image, `java/util/function/Function`, exposing only the public generic abstract SAM `R apply(T)`. No new native binding or interpreter dispatch behavior is introduced. Existing P42 bootstrap images remain in their prior indices and byte form. The profile root/config/package/VM domains move to `P43-FUNCTION`; all non-bootstrap resource, heap, frame, class input and execution budgets remain P42 values.

The extra bootstrap raises the diagnostic combined-class bound from 255 to 256 (105 + 150 + one). This remains representable by the u16 class count; the maximum image index is 255 and remains representable by u8. No raw-class, heap, handle, CP, checkpoint or runtime quota is raised. Raw `java/util/function/Function` is reserved and rejected, regardless of contents. The image omits `compose`, `andThen`, and `identity`; this is an apply-only profile, not a full Java function library.

Generated fixture sources exercise generic direct and inherited interface implementation, bridge dispatch, captured receiver state, identity/null arguments, assignability and null-receiver behavior. These are independent generated-only checks; parent alone owns the frozen original115 replay. This worker does not inspect/copy original payloads.
