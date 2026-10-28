/**
 * NetSuite ERP connect adapter.
 *
 * Signs one OAuth 2.0 client-credentials token request and then reads the
 * SuiteTalk REST metadata catalog. It does not create integration records,
 * does not sign TBA requests, and does not write ERP data.
 *
 * Copyright 2026 OmniMind catalog adapter. Apache-2.0. Not an Oracle product.
 */

import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";

export const PRODUCT = "NetSuite";
export const STABLE_ID = "proto:market:NetSuite";
export const IMPLEMENTED = ["connect"];
export const TOKEN_PATH = "/services/rest/auth/oauth2/v1/token";
export const METADATA_PATH = "/services/rest/record/v1/metadata-catalog";
export const SCOPE = ["rest_webservices"];
export const ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer";
export const ASSERTION_LIFETIME_SECONDS = 300;
export const MAX_BODY_BYTES = 8 * 1024 * 1024;
export const ALGS = {
  PS256: { hash: "sha256", kind: "rsa" },
  PS384: { hash: "sha384", kind: "rsa" },
  PS512: { hash: "sha512", kind: "rsa" },
  ES256: { hash: "sha256", kind: "ec", curve: "prime256v1" },
  ES384: { hash: "sha384", kind: "ec", curve: "secp384r1" },
  ES512: { hash: "sha512", kind: "ec", curve: "secp521r1" },
};

const ACCOUNT_ID = /^[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*$/;
const IDENTIFIER = /^[\x21-\x7E]{1,512}$/;
const REDIRECT = new Set([301, 302, 303, 307, 308]);

export function accountHostLabel(accountId) {
  return accountId.replaceAll("_", "-").toLowerCase();
}

export function expectedHost(accountId) {
  return accountHostLabel(accountId) + ".suitetalk.api.netsuite.com";
}

function setup(message) {
  return { exitCode: 2, stderr: "setup_required: " + message + "\n", stdout: "" };
}

function fail(message) {
  return { exitCode: 1, stderr: "netsuite_error: " + message + "\n", stdout: "" };
}

function ok(payload) {
  return { exitCode: 0, stderr: "", stdout: JSON.stringify(payload) + "\n" };
}

function required(env, name) {
  const value = env[name];
  if (typeof value !== "string" || value.trim() === "") return "";
  return value.trim();
}

function normalizePem(value) {
  let text = value.trim().replace(/^\uFEFF/, "");
  if (!text.includes("\n") && text.includes("\\n")) {
    text = text.replaceAll("\\n", "\n");
  }
  return text;
}

export function readConfig(env) {
  const accountId = required(env, "NETSUITE_ACCOUNT_ID");
  const suiteTalkUrl = required(env, "NETSUITE_SUITETALK_URL");
  const clientId = required(env, "NETSUITE_CLIENT_ID");
  const certificateId = required(env, "NETSUITE_CERTIFICATE_ID");
  const alg = required(env, "NETSUITE_JWT_ALG");
  const privateKeyPem = typeof env.NETSUITE_PRIVATE_KEY_PEM === "string" ? env.NETSUITE_PRIVATE_KEY_PEM : "";
  if (!accountId || !suiteTalkUrl || !clientId || !certificateId || !alg || privateKeyPem.trim() === "") {
    return setup(
      "NETSUITE_ACCOUNT_ID, NETSUITE_SUITETALK_URL, NETSUITE_CLIENT_ID, NETSUITE_CERTIFICATE_ID, NETSUITE_JWT_ALG, and NETSUITE_PRIVATE_KEY_PEM are required. No default and no credential creation.",
    );
  }
  if (!ACCOUNT_ID.test(accountId) || accountId.length > 64) {
    return setup("NETSUITE_ACCOUNT_ID must be the exact account ID, such as 123456 or 123456_SB1.");
  }
  if (!IDENTIFIER.test(clientId) || clientId.includes('"') || clientId.includes("\\")) {
    return setup("NETSUITE_CLIENT_ID must be the integration client ID, with no spaces or quotes.");
  }
  if (!IDENTIFIER.test(certificateId) || certificateId.includes('"') || certificateId.includes("\\")) {
    return setup("NETSUITE_CERTIFICATE_ID must be the certificate ID from the M2M mapping, with no spaces or quotes.");
  }
  if (!Object.hasOwn(ALGS, alg)) {
    return setup("NETSUITE_JWT_ALG must be PS256, PS384, PS512, ES256, ES384, or ES512.");
  }
  const pem = normalizePem(privateKeyPem);
  if (pem.length > 65536 || !pem.includes("-----BEGIN ") || !pem.includes("-----END ")) {
    return setup("NETSUITE_PRIVATE_KEY_PEM must be the private key PEM for the mapped certificate. This adapter does not read a key file.");
  }
  let parsed;
  try {
    parsed = new URL(suiteTalkUrl);
  } catch {
    return setup("NETSUITE_SUITETALK_URL must be the https SuiteTalk origin from Company URLs.");
  }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.search || parsed.hash) {
    return setup("NETSUITE_SUITETALK_URL must be an https origin with no user, query, or fragment.");
  }
  if (parsed.pathname !== "/" && parsed.pathname !== "") {
    return setup("NETSUITE_SUITETALK_URL must be an origin only, with no path.");
  }
  if (parsed.port && parsed.port !== "443") {
    return setup("NETSUITE_SUITETALK_URL must not set a port other than 443.");
  }
  const host = parsed.hostname;
  const expected = expectedHost(accountId);
  if (host !== expected) {
    return setup(
      "NETSUITE_SUITETALK_URL host must be the Company URLs SuiteTalk host " +
        expected +
        ". This adapter does not construct a different account domain and does not send the private key elsewhere.",
    );
  }
  return {
    exitCode: 0,
    config: {
      accountId,
      host,
      origin: "https://" + host,
      clientId,
      certificateId,
      alg,
      privateKeyPem: pem,
    },
  };
}

function signJwt(alg, privateKeyPem, signingInput) {
  const spec = ALGS[alg];
  const key = crypto.createPrivateKey(privateKeyPem);
  if (spec.kind === "rsa") {
    if (key.asymmetricKeyType !== "rsa") {
      throw new Error("key type");
    }
    return crypto.sign(spec.hash, Buffer.from(signingInput), {
      key,
      padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
      saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
    });
  }
  if (key.asymmetricKeyType !== "ec" || key.asymmetricKeyDetails?.namedCurve !== spec.curve) {
    throw new Error("key type");
  }
  return crypto.sign(spec.hash, Buffer.from(signingInput), {
    key,
    dsaEncoding: "ieee-p1363",
  });
}

export function buildClientAssertion(config, nowSeconds, jti) {
  const tokenUrl = config.origin + TOKEN_PATH;
  const header = { typ: "JWT", alg: config.alg, kid: config.certificateId };
  const payload = {
    iss: config.clientId,
    scope: SCOPE,
    aud: tokenUrl,
    jti,
    exp: nowSeconds + ASSERTION_LIFETIME_SECONDS,
    iat: nowSeconds,
  };
  const signingInput =
    Buffer.from(JSON.stringify(header)).toString("base64url") +
    "." +
    Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = signJwt(config.alg, config.privateKeyPem, signingInput);
  return {
    tokenUrl,
    assertion: signingInput + "." + signature.toString("base64url"),
    payload,
  };
}

export function formBody(assertion) {
  const body = new URLSearchParams();
  body.set("grant_type", "client_credentials");
  body.set("client_assertion_type", ASSERTION_TYPE);
  body.set("client_assertion", assertion);
  return body.toString();
}

function tokenErrorCode(body) {
  try {
    const parsed = JSON.parse(body);
    if (parsed && typeof parsed.error === "string" && /^[a-z0-9_]{1,64}$/.test(parsed.error)) {
      return parsed.error;
    }
  } catch {
    return "";
  }
  return "";
}

function headerMap(headers) {
  const out = {};
  if (!headers) return out;
  if (typeof headers.forEach === "function") {
    headers.forEach((value, key) => {
      out[key.toLowerCase()] = value;
    });
    return out;
  }
  for (const [key, value] of Object.entries(headers)) {
    out[key.toLowerCase()] = String(value);
  }
  return out;
}

export async function defaultTransport(request, fetchImpl = globalThis.fetch) {
  const response = await fetchImpl(request.url, {
    method: request.method,
    headers: request.headers,
    body: request.body,
    redirect: "manual",
    signal: AbortSignal.timeout(30_000),
  });
  const buffer = Buffer.from(await response.arrayBuffer());
  return {
    status: response.status,
    headers: headerMap(response.headers),
    body: buffer.length > MAX_BODY_BYTES ? "" : buffer.toString("utf8"),
    truncated: buffer.length > MAX_BODY_BYTES,
  };
}

function parseJson(body) {
  const text = body.replace(/^\uFEFF/, "");
  return JSON.parse(text);
}

export async function connectAccount(env, options = {}) {
  const read = readConfig(env);
  if (read.exitCode !== 0) return read;
  const config = read.config;
  const transport = options.transport ?? defaultTransport;
  const nowSeconds = options.nowSeconds ?? Math.floor(Date.now() / 1000);
  const jti = options.jti ?? crypto.randomBytes(16).toString("hex");
  let signed;
  try {
    signed = buildClientAssertion(config, nowSeconds, jti);
  } catch {
    return setup("NETSUITE_PRIVATE_KEY_PEM does not match NETSUITE_JWT_ALG. No request was sent.");
  }
  let tokenResponse;
  try {
    tokenResponse = await transport({
      method: "POST",
      url: signed.tokenUrl,
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: formBody(signed.assertion),
    });
  } catch {
    return fail("token_request_failed");
  }
  if (!tokenResponse || REDIRECT.has(tokenResponse.status)) {
    return fail("token_redirect_not_followed");
  }
  if (tokenResponse.truncated) {
    return fail("token_response_too_large");
  }
  if (tokenResponse.status !== 200) {
    const code = tokenErrorCode(tokenResponse.body ?? "");
    return fail("token_http_" + tokenResponse.status + (code ? " " + code : ""));
  }
  let token;
  try {
    token = parseJson(tokenResponse.body ?? "");
  } catch {
    return fail("token_response_not_json");
  }
  const accessToken = token && typeof token.access_token === "string" ? token.access_token : "";
  const tokenType = token && typeof token.token_type === "string" ? token.token_type : "";
  if (!accessToken || /\s/.test(accessToken) || accessToken.length > 16384 || tokenType.toLowerCase() !== "bearer") {
    return fail("token_response_missing_bearer");
  }
  if (typeof token.expires_in !== "number" || !Number.isFinite(token.expires_in)) {
    return fail("token_response_missing_expires_in");
  }
  const metadataUrl = config.origin + METADATA_PATH;
  let metadataResponse;
  try {
    metadataResponse = await transport({
      method: "GET",
      url: metadataUrl,
      headers: {
        authorization: "Bearer " + accessToken,
        accept: "application/json",
      },
    });
  } catch {
    return fail("metadata_request_failed");
  }
  if (!metadataResponse || REDIRECT.has(metadataResponse.status)) {
    return fail("metadata_redirect_not_followed");
  }
  if (metadataResponse.truncated) {
    return fail("metadata_response_too_large");
  }
  if (metadataResponse.status !== 200) {
    return fail("metadata_http_" + metadataResponse.status);
  }
  let catalog;
  try {
    catalog = parseJson(metadataResponse.body ?? "");
  } catch {
    return fail("metadata_response_not_json");
  }
  if (!catalog || !Array.isArray(catalog.items)) {
    return fail("metadata_response_missing_items");
  }
  return ok({
    product: PRODUCT,
    stableId: STABLE_ID,
    function: "连接 NetSuite ERP",
    connected: true,
    auth: "oauth2-client-credentials",
    accountId: config.accountId,
    host: config.host,
    tokenExpiresIn: token.expires_in,
    metadataStatus: 200,
    recordTypeCount: catalog.items.length,
  });
}

function isDirectRun() {
  const entry = process.argv[1];
  if (!entry) return false;
  return path.resolve(entry) === fileURLToPath(import.meta.url);
}

export async function main(argv = process.argv.slice(2), env = process.env, options = {}) {
  const command = argv[0] ?? "";
  if (command !== "connect" || argv.length !== 1) {
    return fail("only connect is implemented. No request was sent.");
  }
  return connectAccount(env, options);
}

if (isDirectRun()) {
  const result = await main();
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  process.exitCode = result.exitCode;
}
