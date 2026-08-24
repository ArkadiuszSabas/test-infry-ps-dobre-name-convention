import assert from "node:assert/strict";
import test from "node:test";

import { getPublicConfig } from "./public";

test("public config defaults to the same-origin API proxy and disabled Entra login", () => {
  withPublicConfigEnv({}, () => {
    assert.deepEqual(getPublicConfig(), {
      docmindApiBaseUrl: "/api/docmind",
      isEntraLoginEnabled: false,
    });
  });
});

test("public config reads explicit API origin and Entra login flag", () => {
  withPublicConfigEnv(
    {
      NEXT_PUBLIC_DOCMIND_API_BASE_URL: "https://api.example.test",
      NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED: "true",
    },
    () => {
      assert.deepEqual(getPublicConfig(), {
        docmindApiBaseUrl: "https://api.example.test",
        isEntraLoginEnabled: true,
      });
    },
  );
});

test("public config accepts an explicit same-origin API proxy path", () => {
  withPublicConfigEnv(
    {
      NEXT_PUBLIC_DOCMIND_API_BASE_URL: "/api/docmind/",
    },
    () => {
      assert.deepEqual(getPublicConfig(), {
        docmindApiBaseUrl: "/api/docmind",
        isEntraLoginEnabled: false,
      });
    },
  );
});

test("public config rejects malformed boolean values", () => {
  withPublicConfigEnv(
    {
      NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED: "yes",
    },
    () => {
      assert.throws(
        () => getPublicConfig(),
        /NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED must be true or false/,
      );
    },
  );
});

test("public config rejects API base paths with query strings", () => {
  withPublicConfigEnv(
    {
      NEXT_PUBLIC_DOCMIND_API_BASE_URL: "/api/docmind?target=api",
    },
    () => {
      assert.throws(
        () => getPublicConfig(),
        /NEXT_PUBLIC_DOCMIND_API_BASE_URL must be an API origin or root-relative path without query or hash/,
      );
    },
  );
});

function withPublicConfigEnv(
  values: Partial<Record<string, string>>,
  callback: () => void,
) {
  const previousApiBaseUrl = process.env.NEXT_PUBLIC_DOCMIND_API_BASE_URL;
  const previousEntraEnabled =
    process.env.NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED;

  setEnvValue(
    "NEXT_PUBLIC_DOCMIND_API_BASE_URL",
    values.NEXT_PUBLIC_DOCMIND_API_BASE_URL,
  );
  setEnvValue(
    "NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED",
    values.NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED,
  );

  try {
    callback();
  } finally {
    restoreEnvValue("NEXT_PUBLIC_DOCMIND_API_BASE_URL", previousApiBaseUrl);
    restoreEnvValue(
      "NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED",
      previousEntraEnabled,
    );
  }
}

function setEnvValue(name: string, value: string | undefined) {
  if (value === undefined) {
    delete process.env[name];
    return;
  }

  process.env[name] = value;
}

function restoreEnvValue(name: string, value: string | undefined) {
  if (value === undefined) {
    delete process.env[name];
    return;
  }

  process.env[name] = value;
}
