# EnumSet parent amendment

The recovered DeepSeek candidate fit LOCAL384 and passed the measured mid-`<clinit>` path,
but all three independent Sol-xhigh reviews identified that `_enumUniverse` did not inspect
`initializationState`: an enum could publish `$VALUES`, later fail `<clinit>`, then be
incorrectly recovered. Parent added one bounded state-3 branch using existing guest
NoClassDefFoundError kind12. State0 still atomically refuses because no universe was
published; measured state1 and completed state2 are admitted. The first two direct forms
exceeded LOCAL384; the final existing-kind form compiles at393205B, leaving11B under the
fixed393216 cap. Parent generated failure fixture proves EIIE followed by catchable NCDFE.

Parent also corrected the diagnostic total-class bound111→112 for raw29 plus83 bootstrap
images. No raw/gas/frame/heap/checkpoint/head cap changed. The inherited HashSet iterator is
only claimed for the measured quiescent EnumSet after allOf; broad mutable EnumSet or
snapshot-under-mutation semantics are not claimed.
