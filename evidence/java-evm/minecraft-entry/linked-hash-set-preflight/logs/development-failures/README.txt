Preserved failed development observations (not positive evidence):
- initial-host-oracle-hash-contract.log: Equal lacked hashCode(), so host JDK
  HashSet did not invoke equals across buckets. The generated fixture now returns
  zero hash explicitly; the guest implementation remains intentionally linear.
- initial-coordinator-engine-address.log: coordinator retained the parent fixed
  engine address and honestly reverted MR0Error(3). The rebuilt coordinator pins
  the new LOCAL engine address; the later whole generated gate is the evidence.
