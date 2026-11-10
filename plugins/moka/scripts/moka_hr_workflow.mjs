/**
 * Callable adapter for Moka HR workflow reads and the documented writes.
 * Official contracts retrieved 2026-10-15:
 * - https://www.mokahr.com/docs/api/
 * - https://people.mokahr.com/docs/api/view/v1.html
 * - https://open.mokahr.com/
 *
 * This file does not embed an API key, tenant id, or private key.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import https from "node:https";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const PRODUCT = "Moka";
export const STABLE_ID = "proto:market:Moka";
export const FUNCTION_NAME = "Moka HR 工作流";

export const DOCUMENTED_HOSTS = Object.freeze([
  "api.mokahr.com",
  "api-staging-3.mokahr.com",
  "hire-r1-api.mokahr.com",
]);

export const DEFAULT_ORIGIN = "https://api.mokahr.com";

export const ENDPOINTS = Object.freeze({
  atsPipelinesV2: {
    command: "ats-pipelines",
    method: "GET",
    path: "/api-platform/v2/pipelines/getPipelinesList",
    source: "https://www.mokahr.com/docs/api/",
    title: "获取招聘流程列表",
  },
  atsPipelinesV1: {
    command: "ats-pipelines-v1",
    method: "GET",
    path: "/api-platform/v1/pipelines/list",
    source: "https://www.mokahr.com/docs/api/",
    title: "获取招聘流程列表",
  },
  atsStages: {
    command: "ats-stages",
    method: "GET",
    path: "/api-platform/v2/stage/getStagesList",
    source: "https://www.mokahr.com/docs/api/",
    title: "获取阶段信息列表",
  },
  peopleApprovalForm: {
    command: "people-approval-form",
    method: "POST",
    path: "/api-platform/hcm/oapi/v2/workflow/flowInstance/form-data",
    source: "https://people.mokahr.com/docs/api/view/v1.html",
    title: "审批表单详情数据接口",
  },
  atsMoveStage: {
    command: "ats-move-stage",
    method: "PUT",
    path: "/api-platform/v1/applications/move_application_stage",
    source: "https://www.mokahr.com/docs/api/",
    title: "将申请移动到所在职位下的任一阶段",
  },
  atsCreateOffer: {
    command: "ats-create-offer",
    method: "POST",
    path: "/api-platform/v1/create-offer",
    source: "https://www.mokahr.com/docs/api/",
    title: "创建Offer",
  },
  atsApproveOffer: {
    command: "ats-approve-offer",
    method: "PUT",
    path: "/api-platform/v1/applications/offerApproval",
    source: "https://www.mokahr.com/docs/api/",
    title: "审批offer",
  },
  atsSendOffer: {
    command: "ats-send-offer",
    method: "POST",
    path: "/api-platform/v1/sendOffer",
    source: "https://www.mokahr.com/docs/api/",
    title: "发送offer",
  },
  atsOfferFeedback: {
    command: "ats-offer-feedback",
    method: "PUT",
    path: "/api-platform/v1/offer/status",
    source: "https://www.mokahr.com/docs/api/",
    title: "接收/拒绝Offer",
  },
  atsMarkHired: {
    command: "ats-mark-hired",
    method: "PUT",
    path: "/api-platform/v1/applications/{applicationId}/hired",
    source: "https://www.mokahr.com/docs/api/",
    title: "标记候选人已入职",
  },
  peopleAddJobChange: {
    command: "people-add-job-change",
    method: "POST",
    path: "/api-platform/hcm/oapi/v2/core/rosters/batchAddJobChange",
    source: "https://people.mokahr.com/docs/api/view/v1.html",
    title: "新增员工异动数据接口",
  },
  peopleCreateOnboarding: {
    command: "people-create-onboarding",
    method: "POST",
    path: "/api-platform/hcm/oapi/v1/basic/ob/employee/batchCreate",
    source: "https://people.mokahr.com/docs/api/view/v1.html",
    title: "批量添加待入职员工",
  },
});

const CREATE_OFFER_OPTIONAL = [
  "salaryNumber",
  "salaryType",
  "checkinDate",
  "locationId",
  "contactUserName",
  "contactPhone",
  "contactEmail",
  "customFields",
  "creatorEmail",
  "creatorNumber",
  "toCandidateAttachment",
  "toApproverAttachment",
  "hcId",
  "jobRankId",
  "departmentCode",
  "isCreateOfferAttachment",
  "templateId",
];

const HIRED_OPTIONAL = ["hcId", "isUseOfferHcid", "talentPoolIds"];

const JOB_CHANGE_FIELDS = [
  "employee_uid",
  "effect_date",
  "event_type",
  "event_reason_id",
  "department",
  "report_leader",
  "dashed_report_leader",
  "mentor",
  "position_id",
  "duty_id",
  "duty_level_id",
  "manage_duty_level_id",
  "employee_type_id",
  "months_of_probation_id",
  "office_address_id",
  "leave_detail_reason",
  "leave_handle_remark",
  "leave_event_type",
  "leave_event_reason_id",
  "extend_fields",
];

const ONBOARDING_FIELDS = [
  "employeeNo",
  "realName",
  "onBoardingPlan",
  "department",
  "reportLeader",
  "dutyLevelId",
  "mangeDutyLevelId",
  "employeeTypeId",
  "officeAddressId",
  "positionId",
  "dutyId",
  "onBoardingDate",
  "periodEndDate",
  "monthsOfProbationId",
  "telephoneCountryCode",
  "telephone",
  "personalEmail",
  "idNoIdType",
  "idNo",
  "extendFields",
];

const NONCE_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

export function basicAuthorization(apiKey) {
  const key = String(apiKey ?? "");
  if (!key || /[\s:]/.test(key)) {
    throw new SetupError(
      "MOKA_API_KEY must be a non-empty API key without spaces or a colon. Password stays empty; the colon is added by this adapter.",
    );
  }
  return `Basic ${Buffer.from(`${key}:`, "utf8").toString("base64")}`;
}

export function resolveOrigin(raw) {
  const value = String(raw ?? "").trim();
  if (!value) return DEFAULT_ORIGIN;
  const withScheme = value.includes("://") ? value : `https://${value}`;
  let parsed;
  try {
    parsed = new URL(withScheme);
  } catch {
    throw new SetupError("MOKA_API_HOST is not a URL.");
  }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new SetupError("MOKA_API_HOST must be an https origin with no user, path, query, or fragment.");
  }
  if (!DOCUMENTED_HOSTS.includes(parsed.hostname)) {
    throw new SetupError(
      `MOKA_API_HOST must be one of ${DOCUMENTED_HOSTS.join(", ")}. This adapter does not call an undocumented host.`,
    );
  }
  return `https://${parsed.hostname}`;
}

export function canonicalSignString(params) {
  return Object.keys(params)
    .filter((key) => key !== "sign")
    .sort()
    .map((key) => `${key}=${params[key]}`)
    .join("&");
}

export function toPkcs8Pem(material) {
  const text = String(material ?? "").trim();
  if (!text) {
    throw new SetupError("MOKA_PRIVATE_KEY is unset. People workflow calls need the tenant PKCS#8 private key.");
  }
  if (text.includes("BEGIN")) {
    if (!/BEGIN (RSA )?PRIVATE KEY/.test(text)) {
      throw new SetupError("MOKA_PRIVATE_KEY PEM is not a private key.");
    }
    return text.endsWith("\n") ? text : `${text}\n`;
  }
  const compact = text.replace(/\s+/g, "");
  if (!/^[A-Za-z0-9+/=]+$/.test(compact)) {
    throw new SetupError("MOKA_PRIVATE_KEY must be PKCS#8 base64 or a PEM private key.");
  }
  const lines = compact.match(/.{1,64}/g) ?? [];
  return `-----BEGIN PRIVATE KEY-----\n${lines.join("\n")}\n-----END PRIVATE KEY-----\n`;
}

export function signMd5WithRsa(canonical, privateKeyMaterial) {
  const pem = toPkcs8Pem(privateKeyMaterial);
  const signer = crypto.createSign("RSA-MD5");
  signer.update(canonical, "utf8");
  signer.end();
  try {
    return signer.sign(pem, "base64");
  } catch {
    throw new SetupError("MOKA_PRIVATE_KEY could not produce an MD5withRSA signature. Expected PKCS#8.");
  }
}

export function verifyMd5WithRsa(canonical, signature, publicKeyPem) {
  const verifier = crypto.createVerify("RSA-MD5");
  verifier.update(canonical, "utf8");
  verifier.end();
  return verifier.verify(publicKeyPem, signature, "base64");
}

export class SetupError extends Error {
  constructor(message) {
    super(message);
    this.name = "SetupError";
    this.exitCode = 2;
  }
}

function readPrivateKey(env) {
  const inline = String(env.MOKA_PRIVATE_KEY ?? "").trim();
  const file = String(env.MOKA_PRIVATE_KEY_FILE ?? "").trim();
  if (inline && file) {
    throw new SetupError("Set only one of MOKA_PRIVATE_KEY or MOKA_PRIVATE_KEY_FILE.");
  }
  if (file) {
    if (!path.isAbsolute(file)) {
      throw new SetupError("MOKA_PRIVATE_KEY_FILE must be an absolute path. This adapter does not search a home directory.");
    }
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
      throw new SetupError("MOKA_PRIVATE_KEY_FILE is not a file.");
    }
    return fs.readFileSync(file, "utf8");
  }
  return inline;
}

function requireValue(env, name, label) {
  const value = String(env[name] ?? "").trim();
  if (!value) throw new SetupError(`${name} is unset. ${label}`);
  return value;
}

function flowInstanceId(argv) {
  const flag = argv.indexOf("--flow-instance-id");
  const value = flag >= 0 ? argv[flag + 1] : "";
  if (!/^[1-9]\d{0,18}$/.test(value ?? "")) {
    throw new SetupError("--flow-instance-id must be a positive integer of at most 19 digits.");
  }
  return value;
}

function hireMode(argv) {
  const flag = argv.indexOf("--hire-mode");
  const value = flag >= 0 ? argv[flag + 1] : "";
  if (value !== "1" && value !== "2") {
    throw new SetupError("--hire-mode is required for ats-pipelines-v1: 1 social, 2 campus.");
  }
  return value;
}

function flagValue(argv, name) {
  const index = argv.indexOf(name);
  if (index < 0 || argv[index + 1] === undefined || String(argv[index + 1]).startsWith("--")) return "";
  return String(argv[index + 1]);
}

function positiveId(value, label) {
  if (!/^[1-9]\d{0,18}$/.test(String(value ?? ""))) {
    throw new SetupError(`${label} must be a positive integer of at most 19 digits.`);
  }
  return Number(value);
}

function optionalBoolean(value, label) {
  if (value === "") return undefined;
  if (value !== "true" && value !== "false") throw new SetupError(`${label} must be true or false.`);
  return value === "true";
}

function readBodyFile(argv) {
  const file = flagValue(argv, "--body-file");
  if (!file) return undefined;
  if (!path.isAbsolute(file)) throw new SetupError("--body-file must be an absolute path.");
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) throw new SetupError("--body-file is not a file.");
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    throw new SetupError("--body-file is not JSON.");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new SetupError("--body-file must be a JSON object.");
  }
  return parsed;
}

function pickFields(source, allowed, label) {
  const unknown = Object.keys(source).filter((key) => !allowed.includes(key));
  if (unknown.length) throw new SetupError(`${label} has undocumented fields: ${unknown.join(", ")}`);
  const picked = {};
  for (const key of allowed) {
    if (source[key] !== undefined) picked[key] = source[key];
  }
  return picked;
}

function requireText(value, label) {
  const text = String(value ?? "").trim();
  if (!text) throw new SetupError(`${label} is required.`);
  return text;
}

export function buildJobChangeBody(payload) {
  if (!payload || !Array.isArray(payload.data) || payload.data.length < 1 || payload.data.length > 200) {
    throw new SetupError("job change body data must be an array of 1 to 200 items.");
  }
  return {
    data: payload.data.map((item, index) => {
      if (!item || typeof item !== "object" || Array.isArray(item)) {
        throw new SetupError(`job change item ${index} must be an object.`);
      }
      const picked = pickFields(item, JOB_CHANGE_FIELDS, `job change item ${index}`);
      positiveId(picked.employee_uid, `job change item ${index} employee_uid`);
      requireText(picked.effect_date, `job change item ${index} effect_date`);
      requireText(picked.event_type, `job change item ${index} event_type`);
      return picked;
    }),
  };
}

export function buildOnboardingBody(payload) {
  if (!payload || !Array.isArray(payload.data) || payload.data.length < 1 || payload.data.length > 100) {
    throw new SetupError("onboarding body data must be an array of 1 to 100 items.");
  }
  return {
    data: payload.data.map((item, index) => {
      if (!item || typeof item !== "object" || Array.isArray(item)) {
        throw new SetupError(`onboarding item ${index} must be an object.`);
      }
      const picked = pickFields(item, ONBOARDING_FIELDS, `onboarding item ${index}`);
      requireText(picked.realName, `onboarding item ${index} realName`);
      positiveId(picked.onBoardingPlan, `onboarding item ${index} onBoardingPlan`);
      positiveId(picked.employeeTypeId, `onboarding item ${index} employeeTypeId`);
      requireText(picked.onBoardingDate, `onboarding item ${index} onBoardingDate`);
      requireText(picked.telephoneCountryCode, `onboarding item ${index} telephoneCountryCode`);
      requireText(picked.telephone, `onboarding item ${index} telephone`);
      requireText(picked.personalEmail, `onboarding item ${index} personalEmail`);
      positiveId(picked.idNoIdType, `onboarding item ${index} idNoIdType`);
      requireText(picked.idNo, `onboarding item ${index} idNo`);
      const department = picked.department;
      if (!department || typeof department !== "object" || Array.isArray(department)) {
        throw new SetupError(`onboarding item ${index} department is required.`);
      }
      if (department.departmentId === undefined && !String(department.departmentNo ?? "").trim()) {
        throw new SetupError(`onboarding item ${index} department needs departmentId or departmentNo.`);
      }
      return picked;
    }),
  };
}

function nonce8() {
  const bytes = crypto.randomBytes(8);
  return Array.from(bytes, (byte) => NONCE_ALPHABET[byte % NONCE_ALPHABET.length]).join("");
}

function queryString(params) {
  return Object.keys(params)
    .sort()
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(String(params[key]))}`)
    .join("&");
}

export function defaultRequest({ method, origin, pathAndQuery, headers, body }) {
  const target = new URL(pathAndQuery, origin);
  if (target.origin !== origin) {
    return Promise.reject(new SetupError("Request origin escaped the documented host."));
  }
  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        protocol: target.protocol,
        hostname: target.hostname,
        port: 443,
        path: `${target.pathname}${target.search}`,
        method,
        headers,
        timeout: 20000,
        servername: target.hostname,
      },
      (res) => {
        const chunks = [];
        let size = 0;
        res.on("data", (chunk) => {
          size += chunk.length;
          if (size <= 1_000_000) chunks.push(chunk);
        });
        res.on("end", () => {
          resolve({
            status: res.statusCode ?? 0,
            contentType: String(res.headers["content-type"] ?? ""),
            location: res.headers.location ? String(res.headers.location).split("?")[0] : undefined,
            body: Buffer.concat(chunks),
            truncated: size > 1_000_000,
          });
        });
      },
    );
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

function parseBody(raw, contentType) {
  const text = raw.toString("utf8");
  if (contentType.includes("json") || text.startsWith("{") || text.startsWith("[")) {
    try {
      return JSON.parse(text);
    } catch {
      return { unparsed: text.slice(0, 2000) };
    }
  }
  return { unparsed: text.slice(0, 2000) };
}

function envelope(command, extra) {
  return {
    product: PRODUCT,
    stableId: STABLE_ID,
    function: FUNCTION_NAME,
    command,
    credentialsPrinted: false,
    ...extra,
  };
}

async function callApi(request, { method, origin, pathAndQuery, authorization, body }) {
  const headers = {
    Accept: "application/json",
    Authorization: authorization,
  };
  let payload;
  if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
    headers["Content-Length"] = Buffer.byteLength(payload);
  }
  const response = await request({ method, origin, pathAndQuery, headers, body: payload });
  return {
    httpStatus: response.status,
    contentType: response.contentType,
    locationPath: response.location,
    truncated: response.truncated,
    body: parseBody(response.body, response.contentType),
  };
}

export async function run(argv, env, deps = {}) {
  try {
    return await dispatch(argv, env, deps);
  } catch (error) {
    if (!(error instanceof SetupError)) throw error;
    return {
      exitCode: 2,
      stderr: `${error.message}\n`,
      stdout: envelope(argv[0] || "unknown", {
        liveCall: false,
        state: "setup_required",
        message: error.message,
      }),
    };
  }
}

async function dispatch(argv, env, deps) {
  const request = deps.request ?? defaultRequest;
  const now = deps.now ?? Date.now;
  const makeNonce = deps.nonce ?? nonce8;
  const command = argv[0] || "help";

  if (command === "help" || command === "--help" || command === "-h") {
    return {
      exitCode: 0,
      stdout: envelope("help", {
        liveCall: false,
        commands: [
          "status",
          "ats-pipelines",
          "ats-pipelines-v1 --hire-mode 1|2",
          "ats-stages",
          "people-approval-form --flow-instance-id <positive-integer>",
          "ats-move-stage --application-id <id> --stage-id <id>",
          "ats-create-offer --application-id <id> [--body-file <absolute.json>]",
          "ats-approve-offer --application-id <id> --status 1|2|3",
          "ats-send-offer --application-id <id> --hr-email <email>",
          "ats-offer-feedback --application-id <id> --accepted 0|1 [--reason-id <id>]",
          "ats-mark-hired --application-id <id> --hired-at <time> --probation 0-6",
          "people-add-job-change --body-file <absolute.json>",
          "people-create-onboarding --body-file <absolute.json>",
          "sign-self-check",
          "probe-auth-required",
        ],
      }),
    };
  }

  if (command === "sign-self-check") {
    const { publicKey, privateKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
    const canonical = "apiCode=0001&entCode=1&nonce=999&timestamp=1565244098737";
    const signature = signMd5WithRsa(canonical, privateKey.export({ type: "pkcs8", format: "pem" }));
    const verified = verifyMd5WithRsa(canonical, signature, publicKey.export({ type: "spki", format: "pem" }));
    if (!verified) {
      return { exitCode: 1, stderr: "local MD5withRSA self-check did not verify\n" };
    }
    return {
      exitCode: 0,
      stdout: envelope("sign-self-check", {
        liveCall: false,
        mokaCalled: false,
        algorithm: "MD5withRSA",
        canonical,
        verified: true,
      }),
    };
  }

  if (command === "status") {
    const origin = resolveOrigin(env.MOKA_API_HOST);
    return {
      exitCode: 0,
      stdout: envelope("status", {
        liveCall: false,
        origin,
        apiKeyConfigured: Boolean(String(env.MOKA_API_KEY ?? "").trim()),
        entCodeConfigured: Boolean(String(env.MOKA_ENT_CODE ?? "").trim()),
        apiCodeConfigured: Boolean(String(env.MOKA_API_CODE ?? "").trim()),
        privateKeyConfigured: Boolean(
          String(env.MOKA_PRIVATE_KEY ?? "").trim() || String(env.MOKA_PRIVATE_KEY_FILE ?? "").trim(),
        ),
        state: String(env.MOKA_API_KEY ?? "").trim() ? "configured_not_called" : "setup_required",
      }),
    };
  }

  if (command === "probe-auth-required") {
    const origin = resolveOrigin(env.MOKA_API_HOST);
    const spec = ENDPOINTS.atsPipelinesV2;
    const response = await request({
      method: "GET",
      origin,
      pathAndQuery: spec.path,
      headers: { Accept: "application/json" },
    });
    return {
      exitCode: 0,
      stdout: envelope(command, {
        liveCall: true,
        credentialsSent: false,
        functionPass: false,
        workflowDataRead: false,
        source: spec.source,
        request: { method: "GET", url: `${origin}${spec.path}` },
        httpStatus: response.status,
        contentType: response.contentType,
        locationPath: response.location,
      }),
    };
  }

  const origin = resolveOrigin(env.MOKA_API_HOST);
  const authorization = basicAuthorization(env.MOKA_API_KEY);

  if (command === "ats-pipelines" || command === "ats-stages") {
    const spec = command === "ats-pipelines" ? ENDPOINTS.atsPipelinesV2 : ENDPOINTS.atsStages;
    const result = await callApi(request, {
      method: spec.method,
      origin,
      pathAndQuery: spec.path,
      authorization,
    });
    return {
      exitCode: result.httpStatus >= 200 && result.httpStatus < 300 ? 0 : 3,
      stdout: envelope(command, {
        liveCall: true,
        credentialsSent: true,
        source: spec.source,
        title: spec.title,
        request: { method: spec.method, url: `${origin}${spec.path}` },
        ...result,
      }),
    };
  }

  if (command === "ats-pipelines-v1") {
    const mode = hireMode(argv);
    const spec = ENDPOINTS.atsPipelinesV1;
    const pathAndQuery = `${spec.path}?currentHireMode=${mode}`;
    const result = await callApi(request, {
      method: spec.method,
      origin,
      pathAndQuery,
      authorization,
    });
    return {
      exitCode: result.httpStatus >= 200 && result.httpStatus < 300 ? 0 : 3,
      stdout: envelope(command, {
        liveCall: true,
        credentialsSent: true,
        source: spec.source,
        title: spec.title,
        request: { method: spec.method, url: `${origin}${pathAndQuery}` },
        ...result,
      }),
    };
  }

  if (command === "people-approval-form") {
    const id = flowInstanceId(argv);
    const entCode = requireValue(env, "MOKA_ENT_CODE", "CSM provides the tenant id.");
    const apiCode = requireValue(
      env,
      "MOKA_API_CODE",
      "Create it in Moka People 设置 - 对外接口设置, data source 审批表单详情查询.",
    );
    const privateKey = readPrivateKey(env);
    if (!privateKey.trim()) {
      throw new SetupError("MOKA_PRIVATE_KEY is unset. People workflow calls need the tenant PKCS#8 private key.");
    }
    const params = {
      apiCode,
      entCode,
      nonce: makeNonce(),
      timestamp: String(now()),
    };
    const canonical = canonicalSignString(params);
    params.sign = signMd5WithRsa(canonical, privateKey);
    const spec = ENDPOINTS.peopleApprovalForm;
    const pathAndQuery = `${spec.path}?${queryString(params)}`;
    const result = await callApi(request, {
      method: spec.method,
      origin,
      pathAndQuery,
      authorization,
      body: { flowInstanceId: id },
    });
    return {
      exitCode: result.httpStatus >= 200 && result.httpStatus < 300 ? 0 : 3,
      stdout: envelope(command, {
        liveCall: true,
        credentialsSent: true,
        source: spec.source,
        title: spec.title,
        request: {
          method: spec.method,
          url: `${origin}${spec.path}`,
          queryNames: ["apiCode", "entCode", "nonce", "timestamp", "sign"],
          bodyNames: ["flowInstanceId"],
        },
        signCanonicalExcludedSign: true,
        ...result,
      }),
    };
  }

  if (WRITE_COMMANDS.has(command)) {
    return writeCommand({ command, argv, env, request, origin, authorization, now, makeNonce });
  }

  throw new SetupError(`Unknown command: ${command}`);
}

const WRITE_COMMANDS = new Set([
  "ats-move-stage",
  "ats-create-offer",
  "ats-approve-offer",
  "ats-send-offer",
  "ats-offer-feedback",
  "ats-mark-hired",
  "people-add-job-change",
  "people-create-onboarding",
]);

async function finishWrite(request, input) {
  const result = await callApi(request, input.call);
  return {
    exitCode: result.httpStatus >= 200 && result.httpStatus < 300 ? 0 : 3,
    stdout: envelope(input.command, {
      liveCall: true,
      credentialsSent: true,
      mutatesTenant: true,
      nativeAcceptance: "pending",
      source: input.spec.source,
      title: input.spec.title,
      request: input.summary,
      ...result,
    }),
  };
}

function peopleSignedQuery({ env, now, makeNonce, apiCodeName, apiCodeLabel, userName }) {
  const entCode = requireValue(env, "MOKA_ENT_CODE", "CSM provides the tenant id.");
  const apiCode = requireValue(env, apiCodeName, apiCodeLabel);
  const privateKey = readPrivateKey(env);
  if (!privateKey.trim()) {
    throw new SetupError("MOKA_PRIVATE_KEY is unset. People writes need the tenant PKCS#8 private key.");
  }
  const params = {
    apiCode,
    entCode,
    nonce: makeNonce(),
    timestamp: String(now()),
  };
  if (userName) params.userName = userName;
  params.sign = signMd5WithRsa(canonicalSignString(params), privateKey);
  return params;
}

async function writeCommand({ command, argv, env, request, origin, authorization, now, makeNonce }) {
  if (command === "ats-move-stage") {
    const applicationId = positiveId(flagValue(argv, "--application-id"), "--application-id");
    const stageId = positiveId(flagValue(argv, "--stage-id"), "--stage-id");
    const spec = ENDPOINTS.atsMoveStage;
    const pathAndQuery = `${spec.path}?${queryString({ applicationId, stageId })}`;
    return finishWrite(request, {
      command,
      spec,
      summary: { method: spec.method, url: `${origin}${spec.path}`, queryNames: ["applicationId", "stageId"] },
      call: { method: spec.method, origin, pathAndQuery, authorization },
    });
  }

  if (command === "ats-create-offer") {
    const applicationId = positiveId(flagValue(argv, "--application-id"), "--application-id");
    const extra = readBodyFile(argv) ?? {};
    const body = { applicationId, ...pickFields(extra, CREATE_OFFER_OPTIONAL, "create offer") };
    if (body.salaryType !== undefined && ![1, 2, 3, 4].includes(body.salaryType)) {
      throw new SetupError("salaryType must be 1, 2, 3, or 4.");
    }
    const spec = ENDPOINTS.atsCreateOffer;
    return finishWrite(request, {
      command,
      spec,
      summary: { method: spec.method, url: `${origin}${spec.path}`, bodyNames: Object.keys(body) },
      call: { method: spec.method, origin, pathAndQuery: spec.path, authorization, body },
    });
  }

  if (command === "ats-approve-offer") {
    const applicationId = positiveId(flagValue(argv, "--application-id"), "--application-id");
    const status = flagValue(argv, "--status");
    if (!["1", "2", "3"].includes(status)) {
      throw new SetupError("--status must be 1 approve, 2 reject, or 3 in progress.");
    }
    const spec = ENDPOINTS.atsApproveOffer;
    return finishWrite(request, {
      command,
      spec,
      summary: { method: spec.method, url: `${origin}${spec.path}`, bodyNames: ["applicationId", "status"] },
      call: {
        method: spec.method,
        origin,
        pathAndQuery: spec.path,
        authorization,
        body: { applicationId, status: Number(status) },
      },
    });
  }

  if (command === "ats-send-offer") {
    const applicationId = positiveId(flagValue(argv, "--application-id"), "--application-id");
    const hrEmail = requireText(flagValue(argv, "--hr-email"), "--hr-email");
    if (/\s/.test(hrEmail) || !hrEmail.includes("@")) throw new SetupError("--hr-email must be an email address.");
    const body = { applicationId, hrEmail };
    const notifySms = optionalBoolean(flagValue(argv, "--notify-sms"), "--notify-sms");
    const notifyEmail = optionalBoolean(flagValue(argv, "--notify-email"), "--notify-email");
    const notifyWechat = optionalBoolean(flagValue(argv, "--notify-wechat"), "--notify-wechat");
    if (notifySms !== undefined) body.notifySms = notifySms;
    if (notifyEmail !== undefined) body.notifyEmail = notifyEmail;
    if (notifyWechat !== undefined) body.notifyWechat = notifyWechat;
    const cc = [];
    for (let index = 0; index < argv.length; index += 1) {
      if (argv[index] === "--cc-email") {
        const email = requireText(argv[index + 1], "--cc-email");
        if (/\s/.test(email) || !email.includes("@")) throw new SetupError("--cc-email must be an email address.");
        cc.push(email);
      }
    }
    if (cc.length) body.ccUserEmails = cc;
    const spec = ENDPOINTS.atsSendOffer;
    return finishWrite(request, {
      command,
      spec,
      summary: { method: spec.method, url: `${origin}${spec.path}`, bodyNames: Object.keys(body) },
      call: { method: spec.method, origin, pathAndQuery: spec.path, authorization, body },
    });
  }

  if (command === "ats-offer-feedback") {
    const applicationId = positiveId(flagValue(argv, "--application-id"), "--application-id");
    const accepted = flagValue(argv, "--accepted");
    if (accepted !== "0" && accepted !== "1") throw new SetupError("--accepted must be 1 or 0.");
    const query = { applicationId, accepted };
    const reason = flagValue(argv, "--reason-id");
    if (accepted === "0" && !reason) throw new SetupError("--reason-id is required when --accepted is 0.");
    if (reason) query.reasonId = positiveId(reason, "--reason-id");
    const pool = flagValue(argv, "--talent-pool-id");
    if (pool) query.talentPoolId = positiveId(pool, "--talent-pool-id");
    const fbTime = flagValue(argv, "--fb-time");
    if (fbTime) query.fbTime = fbTime;
    const spec = ENDPOINTS.atsOfferFeedback;
    return finishWrite(request, {
      command,
      spec,
      summary: { method: spec.method, url: `${origin}${spec.path}`, queryNames: Object.keys(query) },
      call: { method: spec.method, origin, pathAndQuery: `${spec.path}?${queryString(query)}`, authorization },
    });
  }

  if (command === "ats-mark-hired") {
    const applicationId = positiveId(flagValue(argv, "--application-id"), "--application-id");
    const hiredAt = requireText(flagValue(argv, "--hired-at"), "--hired-at");
    const probationRaw = flagValue(argv, "--probation");
    if (!/^[0-6]$/.test(probationRaw)) throw new SetupError("--probation must be an integer from 0 through 6.");
    const extra = readBodyFile(argv) ?? {};
    const body = { hiredAt, probation: Number(probationRaw), ...pickFields(extra, HIRED_OPTIONAL, "mark hired") };
    const spec = ENDPOINTS.atsMarkHired;
    return finishWrite(request, {
      command,
      spec,
      summary: {
        method: spec.method,
        url: `${origin}/api-platform/v1/applications/{applicationId}/hired`,
        bodyNames: Object.keys(body),
      },
      call: {
        method: spec.method,
        origin,
        pathAndQuery: `/api-platform/v1/applications/${applicationId}/hired`,
        authorization,
        body,
      },
    });
  }

  if (command === "people-add-job-change" || command === "people-create-onboarding") {
    const fileBody = readBodyFile(argv);
    if (!fileBody) throw new SetupError("--body-file is required.");
    const onboarding = command === "people-create-onboarding";
    const body = onboarding ? buildOnboardingBody(fileBody) : buildJobChangeBody(fileBody);
    const userName = onboarding
      ? ""
      : requireText(env.MOKA_USER_NAME, "MOKA_USER_NAME");
    if (!onboarding && (/\s/.test(userName) || !userName.includes("@"))) {
      throw new SetupError("MOKA_USER_NAME must be the user email required by the job-change query.");
    }
    const params = peopleSignedQuery({
      env,
      now,
      makeNonce,
      apiCodeName: onboarding ? "MOKA_ONBOARDING_API_CODE" : "MOKA_JOB_CHANGE_API_CODE",
      apiCodeLabel: onboarding
        ? "Moka People 设置 - 对外接口设置, data source 批量新增待入职员工."
        : "Moka People 设置 - 对外接口设置, data source 新增异动记录接口.",
      userName,
    });
    const spec = onboarding ? ENDPOINTS.peopleCreateOnboarding : ENDPOINTS.peopleAddJobChange;
    return finishWrite(request, {
      command,
      spec,
      summary: {
        method: spec.method,
        url: `${origin}${spec.path}`,
        queryNames: Object.keys(params).filter((key) => key !== "sign").concat("sign"),
        bodyNames: ["data"],
      },
      call: {
        method: spec.method,
        origin,
        pathAndQuery: `${spec.path}?${queryString(params)}`,
        authorization,
        body,
      },
    });
  }

  throw new SetupError(`Unknown command: ${command}`);
}

function emit(result) {
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.stdout) process.stdout.write(`${JSON.stringify(result.stdout, null, 2)}\n`);
}

async function main() {
  try {
    const result = await run(process.argv.slice(2), process.env);
    emit(result);
    process.exitCode = result.exitCode;
  } catch (error) {
    const setup = error instanceof SetupError || error?.exitCode === 2;
    const payload = envelope(process.argv[2] || "unknown", {
      liveCall: false,
      state: setup ? "setup_required" : "error",
      message: setup ? error.message : "request failed",
    });
    if (!setup) payload.detail = String(error?.message || error).slice(0, 300);
    process.stderr.write(`${error.message}\n`);
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    process.exitCode = setup ? 2 : 3;
  }
}

const selfPath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(selfPath)) {
  main();
}
