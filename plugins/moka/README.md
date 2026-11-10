# moka

Callable adapter for the prototype row Moka / `proto:market:Moka` / Moka HR 工作流.

It calls the official Moka OpenAPI documented at https://www.mokahr.com/docs/api/ and https://people.mokahr.com/docs/api/view/v1.html. The open platform index is https://open.mokahr.com/.

```text
node scripts/moka_hr_workflow.mjs status
node scripts/moka_hr_workflow.mjs ats-pipelines
node scripts/moka_hr_workflow.mjs people-approval-form --flow-instance-id <id>
```

Without `MOKA_API_KEY` the process exits 2 and does not send a request. People calls also need `MOKA_ENT_CODE`, the data-source `apiCode`, and a PKCS#8 private key. Job change also needs `MOKA_USER_NAME`. This package does not ship those values.

Write commands are `ats-move-stage`, `ats-create-offer`, `ats-approve-offer`, `ats-send-offer`, `ats-offer-feedback`, `ats-mark-hired`, `people-add-job-change`, and `people-create-onboarding`. They are not run by the package checks. A real tenant account is still required before acceptance.

See `SOURCE.json` for the pinned endpoints, license split, and icon provenance.
