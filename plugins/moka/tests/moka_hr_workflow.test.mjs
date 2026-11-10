import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  basicAuthorization,
  buildJobChangeBody,
  buildOnboardingBody,
  canonicalSignString,
  resolveOrigin,
  run,
  signMd5WithRsa,
  verifyMd5WithRsa,
  SetupError,
} from "../scripts/moka_hr_workflow.mjs";
import crypto from "node:crypto";

test("basic auth uses apiKey colon and empty password", () => {
  const header = basicAuthorization("fixture-key");
  assert.equal(header, `Basic ${Buffer.from("fixture-key:", "utf8").toString("base64")}`);
  assert.notEqual(header, `Basic ${Buffer.from("fixture-key", "utf8").toString("base64")}`);
});

test("basic auth rejects empty and colon", () => {
  assert.throws(() => basicAuthorization(""), SetupError);
  assert.throws(() => basicAuthorization("a:b"), SetupError);
});

test("origin allowlist keeps the documented China host and rejects others", () => {
  assert.equal(resolveOrigin(""), "https://api.mokahr.com");
  assert.equal(resolveOrigin("https://hire-r1-api.mokahr.com"), "https://hire-r1-api.mokahr.com");
  assert.throws(() => resolveOrigin("http://api.mokahr.com"), SetupError);
  assert.throws(() => resolveOrigin("https://example.com"), SetupError);
  assert.throws(() => resolveOrigin("https://api.mokahr.com/api-platform"), SetupError);
});

test("canonical string matches the People sign examples and drops sign", () => {
  assert.equal(
    canonicalSignString({
      nonce: "999",
      timestamp: "1565244098737",
      entCode: "1",
      apiCode: "0001",
      sign: "ignored",
    }),
    "apiCode=0001&entCode=1&nonce=999&timestamp=1565244098737",
  );
  assert.equal(
    canonicalSignString({
      userName: "xiao@qq.com",
      nonce: "999",
      timestamp: "1565244098737",
      entCode: "1",
      apiCode: "0001",
    }),
    "apiCode=0001&entCode=1&nonce=999&timestamp=1565244098737&userName=xiao@qq.com",
  );
});

test("MD5withRSA roundtrip uses an ephemeral key and does not call Moka", () => {
  const { publicKey, privateKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const canonical = "apiCode=0001&entCode=1&nonce=999&timestamp=1565244098737";
  const signature = signMd5WithRsa(canonical, privateKey.export({ type: "pkcs8", format: "pem" }));
  assert.equal(
    verifyMd5WithRsa(canonical, signature, publicKey.export({ type: "spki", format: "pem" })),
    true,
  );
  assert.equal(
    verifyMd5WithRsa(`${canonical}&userName=other`, signature, publicKey.export({ type: "spki", format: "pem" })),
    false,
  );
});

test("missing API key does not send a request", async () => {
  let called = false;
  const result = await run(["ats-pipelines"], {}, {
    request() {
      called = true;
      throw new Error("network");
    },
  });
  assert.equal(called, false);
  assert.equal(result.exitCode, 2);
  assert.equal(result.stdout.state, "setup_required");
  assert.equal(result.stdout.liveCall, false);
});

test("people approval form stays local when tenant fields are missing", async () => {
  let called = false;
  const result = await run(
    ["people-approval-form", "--flow-instance-id", "619481843815727104"],
    { MOKA_API_KEY: "fixture-key" },
    {
      request() {
        called = true;
        throw new Error("network");
      },
    },
  );
  assert.equal(called, false);
  assert.equal(result.exitCode, 2);
});

test("configured ATS pipeline request uses the documented path and basic header", async () => {
  const seen = [];
  const result = await run(["ats-pipelines"], { MOKA_API_KEY: "fixture-key" }, {
    request(input) {
      seen.push(input);
      return Promise.resolve({
        status: 401,
        contentType: "application/json",
        body: Buffer.from('{"code":401,"msg":"unauthorized"}'),
      });
    },
  });
  assert.equal(seen.length, 1);
  assert.equal(seen[0].method, "GET");
  assert.equal(seen[0].origin, "https://api.mokahr.com");
  assert.equal(seen[0].pathAndQuery, "/api-platform/v2/pipelines/getPipelinesList");
  assert.equal(seen[0].headers.Authorization, basicAuthorization("fixture-key"));
  assert.equal(result.exitCode, 3);
  assert.equal(result.stdout.httpStatus, 401);
  assert.equal(JSON.stringify(result.stdout).includes("fixture-key"), false);
});

test("people approval request signs documented query names and posts flowInstanceId", async () => {
  const seen = [];
  const { privateKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const pem = privateKey.export({ type: "pkcs8", format: "pem" });
  const result = await run(
    ["people-approval-form", "--flow-instance-id", "619481843815727104"],
    {
      MOKA_API_KEY: "fixture-key",
      MOKA_ENT_CODE: "ent-fixture",
      MOKA_API_CODE: "api-fixture",
      MOKA_PRIVATE_KEY: pem,
    },
    {
      now: () => 1565244098737,
      nonce: () => "ab12CD34",
      request(input) {
        seen.push(input);
        return Promise.resolve({
          status: 200,
          contentType: "application/json",
          body: Buffer.from('{"code":0,"msg":"成功","data":{"flowInstanceId":"619481843815727104"}}'),
        });
      },
    },
  );
  assert.equal(result.exitCode, 0);
  const url = new URL(seen[0].pathAndQuery, seen[0].origin);
  assert.equal(url.pathname, "/api-platform/hcm/oapi/v2/workflow/flowInstance/form-data");
  assert.equal(url.searchParams.get("entCode"), "ent-fixture");
  assert.equal(url.searchParams.get("apiCode"), "api-fixture");
  assert.equal(url.searchParams.get("nonce"), "ab12CD34");
  assert.equal(url.searchParams.get("timestamp"), "1565244098737");
  assert.equal(seen[0].body, '{"flowInstanceId":"619481843815727104"}');
  const signature = url.searchParams.get("sign");
  const publicKey = crypto.createPublicKey(pem);
  assert.equal(
    verifyMd5WithRsa(
      "apiCode=api-fixture&entCode=ent-fixture&nonce=ab12CD34&timestamp=1565244098737",
      signature,
      publicKey.export({ type: "spki", format: "pem" }),
    ),
    true,
  );
  assert.equal(JSON.stringify(result.stdout).includes("fixture-key"), false);
  assert.equal(JSON.stringify(result.stdout).includes("BEGIN PRIVATE KEY"), false);
});

function jsonFile(payload) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "moka-k05-"));
  const file = path.join(dir, "body.json");
  fs.writeFileSync(file, JSON.stringify(payload));
  return file;
}

function mockOk() {
  const seen = [];
  return {
    seen,
    request(input) {
      seen.push(input);
      return Promise.resolve({ status: 200, contentType: "application/json", body: Buffer.from('{"success":true}') });
    },
  };
}

test("write commands do not call the network without an API key", async () => {
  let called = false;
  const result = await run(["ats-move-stage", "--application-id", "96", "--stage-id", "4"], {}, {
    request() {
      called = true;
      throw new Error("network");
    },
  });
  assert.equal(called, false);
  assert.equal(result.exitCode, 2);
  assert.equal(result.stdout.liveCall, false);
});

test("stage move uses the documented PUT query", async () => {
  const { seen, request } = mockOk();
  const result = await run(
    ["ats-move-stage", "--application-id", "96", "--stage-id", "4"],
    { MOKA_API_KEY: "fixture-key" },
    { request },
  );
  assert.equal(result.exitCode, 0);
  assert.equal(result.stdout.nativeAcceptance, "pending");
  assert.equal(result.stdout.mutatesTenant, true);
  assert.equal(seen[0].method, "PUT");
  assert.equal(seen[0].pathAndQuery, "/api-platform/v1/applications/move_application_stage?applicationId=96&stageId=4");
  assert.equal(seen[0].headers.Authorization, basicAuthorization("fixture-key"));
});

test("offer approval, send, feedback, and hired use documented contracts", async () => {
  const { seen, request } = mockOk();
  const env = { MOKA_API_KEY: "fixture-key" };
  await run(["ats-approve-offer", "--application-id", "12", "--status", "1"], env, { request });
  await run(
    ["ats-send-offer", "--application-id", "1234", "--hr-email", "hr@example.com", "--notify-email", "true"],
    env,
    { request },
  );
  await run(["ats-offer-feedback", "--application-id", "89", "--accepted", "0", "--reason-id", "1"], env, { request });
  await run(
    ["ats-mark-hired", "--application-id", "33582", "--hired-at", "2018-08-06T16:00:00.000Z", "--probation", "3"],
    env,
    { request },
  );
  assert.equal(seen[0].method, "PUT");
  assert.equal(seen[0].pathAndQuery, "/api-platform/v1/applications/offerApproval");
  assert.equal(seen[0].body, '{"applicationId":12,"status":1}');
  assert.equal(seen[1].method, "POST");
  assert.equal(seen[1].pathAndQuery, "/api-platform/v1/sendOffer");
  assert.deepEqual(JSON.parse(seen[1].body), {
    applicationId: 1234,
    hrEmail: "hr@example.com",
    notifyEmail: true,
  });
  assert.equal(seen[2].method, "PUT");
  assert.equal(seen[2].pathAndQuery, "/api-platform/v1/offer/status?accepted=0&applicationId=89&reasonId=1");
  assert.equal(seen[3].pathAndQuery, "/api-platform/v1/applications/33582/hired");
  assert.deepEqual(JSON.parse(seen[3].body), { hiredAt: "2018-08-06T16:00:00.000Z", probation: 3 });
});

test("rejected offer feedback requires reasonId and does not send", async () => {
  let called = false;
  const result = await run(
    ["ats-offer-feedback", "--application-id", "89", "--accepted", "0"],
    { MOKA_API_KEY: "fixture-key" },
    {
      request() {
        called = true;
        throw new Error("network");
      },
    },
  );
  assert.equal(called, false);
  assert.equal(result.exitCode, 2);
});

test("people job change signs userName and posts the documented body", async () => {
  const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const file = jsonFile({
    data: [{ employee_uid: 75784573, event_type: "调动", effect_date: "2024-10-15", duty_id: 3047 }],
  });
  const { seen, request } = mockOk();
  const result = await run(["people-add-job-change", "--body-file", file], {
    MOKA_API_KEY: "fixture-key",
    MOKA_ENT_CODE: "ent-fixture",
    MOKA_JOB_CHANGE_API_CODE: "job-code",
    MOKA_USER_NAME: "hr@example.com",
    MOKA_PRIVATE_KEY: privateKey.export({ type: "pkcs8", format: "pem" }),
  }, {
    request,
    now: () => 1565244098737,
    nonce: () => "ab12CD34",
  });
  assert.equal(result.exitCode, 0);
  const url = new URL(seen[0].pathAndQuery, seen[0].origin);
  assert.equal(url.pathname, "/api-platform/hcm/oapi/v2/core/rosters/batchAddJobChange");
  assert.equal(url.searchParams.get("userName"), "hr@example.com");
  assert.equal(
    verifyMd5WithRsa(
      "apiCode=job-code&entCode=ent-fixture&nonce=ab12CD34&timestamp=1565244098737&userName=hr@example.com",
      url.searchParams.get("sign"),
      publicKey.export({ type: "spki", format: "pem" }),
    ),
    true,
  );
  assert.deepEqual(JSON.parse(seen[0].body), {
    data: [{ employee_uid: 75784573, event_type: "调动", effect_date: "2024-10-15", duty_id: 3047 }],
  });
  assert.equal(JSON.stringify(result.stdout).includes("BEGIN PRIVATE KEY"), false);
});

test("people onboarding posts the documented create body and rejects a short body locally", () => {
  assert.throws(() => buildOnboardingBody({ data: [{ realName: "摩小卡" }] }), SetupError);
  const body = buildOnboardingBody({
    data: [{
      realName: "摩小卡",
      onBoardingPlan: 5,
      employeeTypeId: 1,
      onBoardingDate: "2024-05-11T00:00:00",
      telephoneCountryCode: "+86",
      telephone: "13800000000",
      personalEmail: "person@example.com",
      idNoIdType: 3,
      idNo: "fixture-id",
      department: { departmentNo: "NO.1" },
    }],
  });
  assert.equal(body.data[0].department.departmentNo, "NO.1");
  assert.throws(() => buildJobChangeBody({ data: [{ employee_uid: 1 }] }), SetupError);
});

test("probe does not attach authorization", async () => {
  const seen = [];
  const result = await run(["probe-auth-required"], {}, {
    request(input) {
      seen.push(input);
      return Promise.resolve({ status: 401, contentType: "application/json", body: Buffer.from("{}") });
    },
  });
  assert.equal(seen[0].headers.Authorization, undefined);
  assert.equal(result.stdout.credentialsSent, false);
  assert.equal(result.stdout.functionPass, false);
});
