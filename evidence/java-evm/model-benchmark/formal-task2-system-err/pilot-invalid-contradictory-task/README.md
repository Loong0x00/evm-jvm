# Invalid task2 pilot (preserved, excluded)

The parent stopped both candidate runs promptly after discovering a contradiction in its frozen task: it required changing `java/lang/System` to add `err`, while also requiring byte-for-byte preservation/append-only proof of all first83 images including System. No candidate source edits or commits existed at termination. Partial instrumentation is retained and excluded from comparison/selection.

A separate 1.215-second DeepSeek launch used an invalid provider model ID and returned HTTP400 before producing any assistant output; that setup failure is also retained and excluded. The valid provider alias is `deepseek/deepseek-flash`.
