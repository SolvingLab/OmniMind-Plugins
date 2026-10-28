/**
 * Local protocol check. Synthetic keys and an injected transport only.
 * This does not call suitetalk.api.netsuite.com.
 */

import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  ALGS,
  ASSERTION_LIFETIME_SECONDS,
  ASSERTION_TYPE,
  METADATA_PATH,
  SCOPE,
  TOKEN_PATH,
  buildClientAssertion,
  connectAccount,
  defaultTransport,
  expectedHost,
  formBody,
  readConfig,
} from "../scripts/launch.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const LAUNCH = path.join(ROOT, "scripts", "launch.mjs");
const ACCOUNT = "123456_SB1";
const HOST = "123456-sb1.suitetalk.api.netsuite.com";
const ORIGIN = "https://" + HOST;
const CLIENT_ID = "synthetic-client-id-not-live";
const CERTIFICATE_ID = "synthetic-certificate-id";
const NOW = 1_700_000_000;
const JTI = "fixturejti0123456789abcdef";

const results = [];

function check(name, ok, detail) {
  results.push({ name, ok: Boolean(ok), ...(detail ? { detail } : {}) });
}

function pem(key) {
  return key.export({ type: "pkcs8", format: "pem" });
}

function keys() {
  const rsa = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const p256 = crypto.generateKeyPairSync("ec", { namedCurve: "prime256v1" });
  const p384 = crypto.generateKeyPairSync("ec", { namedCurve: "secp384r1" });
  const p521 = crypto.generateKeyPairSync("ec", { namedCurve: "secp521r1" });
  return {
    PS256: rsa,
    PS384: rsa,
    PS512: rsa,
    ES256: p256,
    ES384: p384,
    ES512: p521,
  };
}

function envFor(alg, privateKeyPem, overrides = {}) {
  return {
    NETSUITE_ACCOUNT_ID: ACCOUNT,
    NETSUITE_SUITETALK_URL: ORIGIN,
    NETSUITE_CLIENT_ID: CLIENT_ID,
    NETSUITE_CERTIFICATE_ID: CERTIFICATE_ID,
    NETSUITE_JWT_ALG: alg,
    NETSUITE_PRIVATE_KEY_PEM: privateKeyPem,
    ...overrides,
  };
}

function verify(alg, publicKey, assertion) {
  const spec = ALGS[alg];
  const [h, p, s] = assertion.split(".");
  const signingInput = Buffer.from(h + "." + p);
  const signature = Buffer.from(s, "base64url");
  if (spec.kind === "rsa") {
    return crypto.verify(spec.hash, signingInput, {
      key: publicKey,
      padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
      saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
    }, signature);
  }
  return crypto.verify(spec.hash, signingInput, {
    key: publicKey,
    dsaEncoding: "ieee-p1363",
  }, signature);
}

function decode(part) {
  return JSON.parse(Buffer.from(part, "base64url").toString("utf8"));
}

function leaked(text, secret) {
  return text.includes(secret) || text.includes("PRIVATE KEY") || text.includes("eyJ");
}

const generated = keys();
const psPem = pem(generated.PS256.privateKey);
const esPem = pem(generated.ES256.privateKey);

check("documented-host-transform", [
  expectedHost("123456") === "123456.suitetalk.api.netsuite.com",
  expectedHost("123456_SB1") === "123456-sb1.suitetalk.api.netsuite.com",
  expectedHost("123456_RP") === "123456-rp.suitetalk.api.netsuite.com",
  expectedHost("3604360_SB1") === "3604360-sb1.suitetalk.api.netsuite.com",
].every(Boolean));

const missing = readConfig({});
check("missing-config-no-origin", missing.exitCode === 2 && missing.stderr.startsWith("setup_required:"));

const badHosts = [
  "http://123456-sb1.suitetalk.api.netsuite.com",
  "https://user:secret@123456-sb1.suitetalk.api.netsuite.com",
  "https://123456-sb1.suitetalk.api.netsuite.com/services/rest",
  "https://123456-sb1.suitetalk.api.netsuite.com?x=1",
  "https://evil.example",
  "https://123456.suitetalk.api.netsuite.com",
  "https://123456-sb1.suitetalk.api.netsuite.com.evil.example",
  "https://123456-sb1.restlets.api.netsuite.com",
];
check(
  "reject-non-company-origin",
  badHosts.every((url) => readConfig(envFor("PS256", psPem, { NETSUITE_SUITETALK_URL: url })).exitCode === 2),
);

check(
  "reject-unknown-alg",
  readConfig(envFor("HS256", psPem)).exitCode === 2,
);

let signatureOk = true;
for (const alg of Object.keys(ALGS)) {
  const pair = generated[alg];
  const config = readConfig(envFor(alg, pem(pair.privateKey))).config;
  const signed = buildClientAssertion(config, NOW, JTI);
  const [h, p] = signed.assertion.split(".");
  const header = decode(h);
  const payload = decode(p);
  signatureOk &&= header.typ === "JWT" && header.alg === alg && header.kid === CERTIFICATE_ID;
  signatureOk &&= payload.iss === CLIENT_ID;
  signatureOk &&= JSON.stringify(payload.scope) === JSON.stringify(SCOPE);
  signatureOk &&= payload.aud === ORIGIN + TOKEN_PATH;
  signatureOk &&= payload.jti === JTI;
  signatureOk &&= payload.iat === NOW && payload.exp === NOW + ASSERTION_LIFETIME_SECONDS;
  signatureOk &&= payload.exp - payload.iat < 3600;
  signatureOk &&= verify(alg, pair.publicKey, signed.assertion);
}
check("jwt-matches-documented-claims-and-verifies", signatureOk);

const samplePrefix =
  "grant_type=client_credentials&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer&client_assertion=";
const body = formBody("abc.def.ghi");
check(
  "form-body-matches-sample-encoding",
  body.startsWith(samplePrefix) && body.endsWith("abc.def.ghi") && body.includes(encodeURIComponent(ASSERTION_TYPE)),
);

function recordingTransport(script) {
  const calls = [];
  return {
    calls,
    async transport(request) {
      calls.push(request);
      return script(request, calls.length);
    },
  };
}

const happy = recordingTransport(() => ({
  status: 200,
  body: callsBody(),
}));
function callsBody() {
  if (happy.calls.length === 1) {
    return JSON.stringify({ access_token: "fixture-access-token", expires_in: 3600, token_type: "Bearer" });
  }
  return JSON.stringify({ items: [{ name: "customer" }, { name: "salesOrder" }] });
}
const connected = await connectAccount(envFor("ES256", esPem), {
  transport: happy.transport,
  nowSeconds: NOW,
  jti: JTI,
});
const connectedJson = connected.exitCode === 0 ? JSON.parse(connected.stdout) : null;
check("connect-two-calls", happy.calls.length === 2 && connected.exitCode === 0 && connectedJson?.connected === true);
const postedAssertion = happy.calls[0]?.body?.slice(samplePrefix.length) ?? "";
check(
  "token-post-shape",
  happy.calls[0]?.method === "POST" &&
    happy.calls[0].url === ORIGIN + TOKEN_PATH &&
    happy.calls[0].headers["content-type"] === "application/x-www-form-urlencoded" &&
    !happy.calls[0].headers.authorization &&
    happy.calls[0].body.startsWith(samplePrefix) &&
    verify("ES256", generated.ES256.publicKey, postedAssertion) &&
    !happy.calls[0].body.includes(esPem),
);
check(
  "metadata-get-bearer-only",
  happy.calls[1]?.method === "GET" &&
    happy.calls[1].url === ORIGIN + METADATA_PATH &&
    happy.calls[1].headers.authorization === "Bearer fixture-access-token" &&
    happy.calls[1].headers.accept === "application/json" &&
    happy.calls[1].body === undefined,
);
check(
  "success-omits-secrets",
  connectedJson?.recordTypeCount === 2 &&
    connectedJson.accountId === ACCOUNT &&
    connectedJson.host === HOST &&
    connectedJson.auth === "oauth2-client-credentials" &&
    !leaked(connected.stdout + connected.stderr, esPem) &&
    !connected.stdout.includes("fixture-access-token") &&
    !connected.stdout.includes(CLIENT_ID),
);

async function noSecond(name, first) {
  const rec = recordingTransport(() => first);
  const result = await connectAccount(envFor("PS256", psPem), { transport: rec.transport, nowSeconds: NOW, jti: JTI });
  const text = result.stdout + result.stderr;
  check(name, rec.calls.length === 1 && result.exitCode === 1 && !leaked(text, psPem) && !text.includes(CLIENT_ID));
}
await noSecond("token-401-no-metadata", { status: 401, body: JSON.stringify({ error: "invalid_client", error_description: CLIENT_ID }) });
await noSecond("token-307-not-followed", { status: 307, headers: { location: "https://evil.example/token" }, body: "" });
await noSecond("token-non-json", { status: 200, body: "not-json" });

const redirectMeta = recordingTransport((request, n) => {
  if (n === 1) return { status: 200, body: JSON.stringify({ access_token: "fixture-access-token", expires_in: 3600, token_type: "Bearer" }) };
  return { status: 307, headers: { location: "https://evil.example/metadata" }, body: "" };
});
const redirectMetaResult = await connectAccount(envFor("PS256", psPem), {
  transport: redirectMeta.transport,
  nowSeconds: NOW,
  jti: JTI,
});
check(
  "metadata-307-not-followed",
  redirectMeta.calls.length === 2 &&
    redirectMetaResult.exitCode === 1 &&
    redirectMetaResult.stderr.includes("metadata_redirect_not_followed") &&
    !redirectMeta.calls.some((call) => call.url.includes("evil.example")),
);

const missingItems = recordingTransport((request, n) => {
  if (n === 1) return { status: 200, body: JSON.stringify({ access_token: "fixture-access-token", expires_in: 3600, token_type: "bearer" }) };
  return { status: 200, body: JSON.stringify({ links: [] }) };
});
const missingItemsResult = await connectAccount(envFor("PS256", psPem), {
  transport: missingItems.transport,
  nowSeconds: NOW,
  jti: JTI,
});
check("metadata-without-items-not-connected", missingItemsResult.exitCode === 1 && !missingItemsResult.stdout.includes("connected"));

let calls = 0;
const mismatch = await connectAccount(envFor("PS256", psPem, { NETSUITE_SUITETALK_URL: "https://evil.example" }), {
  transport() {
    calls += 1;
    return { status: 200, body: "{}" };
  },
});
check("host-mismatch-sends-nothing", calls === 0 && mismatch.exitCode === 2);

const escapedPem = esPem.replaceAll("\n", "\\n");
const escapedCalls = [];
const escapedResult = await connectAccount(envFor("ES256", escapedPem), {
  transport(request) {
    escapedCalls.push(request);
    if (escapedCalls.length === 1) {
      return { status: 200, body: JSON.stringify({ access_token: "fixture-access-token", expires_in: 3600, token_type: "Bearer" }) };
    }
    return { status: 200, body: JSON.stringify({ items: [] }) };
  },
  nowSeconds: NOW,
  jti: JTI,
});
check(
  "escaped-pem-newlines-still-sign",
  escapedResult.exitCode === 0 &&
    verify("ES256", generated.ES256.publicKey, escapedCalls[0].body.slice(samplePrefix.length)) &&
    !escapedResult.stdout.includes("PRIVATE KEY"),
);

let keyCalls = 0;
const wrongKey = await connectAccount(envFor("ES256", psPem), {
  transport() {
    keyCalls += 1;
    return { status: 200, body: "{}" };
  },
});
check("alg-key-mismatch-sends-nothing", keyCalls === 0 && wrongKey.exitCode === 2);

let writeCalls = 0;
const launch = await import("../scripts/launch.mjs");
const rejected = await launch.main(["create"], envFor("PS256", psPem), {
  transport() {
    writeCalls += 1;
    return { status: 200, body: "{}" };
  },
});
const suiteql = await launch.main(["suiteql", "--q", "select 1"], envFor("PS256", psPem), {
  transport() {
    writeCalls += 1;
    return { status: 200, body: "{}" };
  },
});
check(
  "create-and-suiteql-rejected-no-request",
  rejected.exitCode === 1 &&
    suiteql.exitCode === 1 &&
    rejected.stderr.includes("only connect") &&
    writeCalls === 0,
);

const emptyEnv = { ...process.env };
for (const name of Object.keys(emptyEnv)) {
  if (name.startsWith("NETSUITE_")) delete emptyEnv[name];
}
const cli = spawnSync(process.execPath, [LAUNCH, "connect"], { env: emptyEnv, encoding: "utf8" });
check(
  "cli-missing-credentials-exit-2",
  cli.status === 2 && cli.stderr.includes("setup_required:") && cli.stdout === "",
);

const cliReject = spawnSync(process.execPath, [LAUNCH, "suiteql"], {
  env: envFor("PS256", psPem),
  encoding: "utf8",
});
check(
  "cli-suiteql-no-output-secrets",
  cliReject.status === 1 &&
    cliReject.stderr.includes("only connect") &&
    !leaked(cliReject.stdout + cliReject.stderr, psPem),
);

let fetchCalls = 0;
const transportResult = await defaultTransport(
  { method: "GET", url: "https://127.0.0.1/unused", headers: {} },
  async (_url, init) => {
    fetchCalls += 1;
    check("default-transport-manual-redirect", init.redirect === "manual" && init.method === "GET");
    return {
      status: 307,
      headers: { forEach(fn) { fn("https://evil.example", "location"); } },
      async arrayBuffer() {
        return new Uint8Array();
      },
    };
  },
);
check("default-transport-returns-307", fetchCalls === 1 && transportResult.status === 307);

const failed = results.filter((item) => !item.ok);
for (const item of results) {
  console.log((item.ok ? "PASS " : "FAIL ") + item.name);
}
if (failed.length) {
  console.error(JSON.stringify(failed));
  process.exitCode = 1;
}
