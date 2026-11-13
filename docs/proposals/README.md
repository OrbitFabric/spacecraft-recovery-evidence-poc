# Initial design documents

These are the two **author-prepared discussion drafts** exchanged for joint technical review. They represent the initial proposal **before** Gonçalo's detailed G0 follow-up, and must not be mistaken for approved specifications or as-run evidence.

The PDFs are prepared for upload to this directory. The following fingerprints identify the exact originals.

| Proposed repository filename | Pages | SHA-256 |
| --- | ---: | --- |
| [`OrbitFabric_OpenOBSW_OpenSVF_Joint_Concept_Note_20261110.pdf`](OrbitFabric_OpenOBSW_OpenSVF_Joint_Concept_Note_20261110.pdf) | 5 | `2932b66de45ebc30e0234c2b07b7161694824a1c8db87ce03e7c597fb522b7d1` |
| [`OrbitFabric_OpenOBSW_OpenSVF_Experimental_Design_Proposal_20261110.pdf`](OrbitFabric_OpenOBSW_OpenSVF_Experimental_Design_Proposal_20261110.pdf) | 8 | `837c0bdac43ce37b34c3b0e303d1c6051252ddbfc6da53a70c3921b1933fcf0c` |

**Status: Uploaded and verified.** Both PDFs are now present in this directory. Their Git blob IDs match the hashes computed from the original local files (respectively `ea7115c6ef751fd2adf77935cf715247150f93f9` for the Concept Note and `a46a8e56abde3bd604621826420686a7a490f4fa` for the Experimental Design Proposal). The SHA-256 values above identify the unchanged original bytes.

Once uploaded, verify the files against the hashes above. No change to the PDF is implied by the repository index.

## Relationship to current design

- [G0 audit and upstream blockers](../../issues/1) records technical constraints discovered during the follow-up review.
- [G1 minimal Evidence Bundle](../../issues/2) starts from actual producer-owned observations.
- [G1 TM observability](../../issues/3) qualifies the `add_tm_listener` path and HK/event decoding.
- [G1 recovery criteria](../../issues/4) defines independent assessment semantics.

A later approved revision should be committed as a **new, versioned document**, preserving these historical discussion drafts. Licensing and attribution conventions remain subject to joint agreement.
