import { existsSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";

import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const defaultConnectorConfigurationRegistry = resolve(
  process.cwd(),
  "src/lib/connector-configurations/registry.ts",
);
const connectorConfigurationRegistryAlias =
  "@docmind/connector-configuration-registry";

function connectorProfilePath(): string | undefined {
  const configuredProfilePath =
    process.env.DOCMIND_CONNECTOR_PROFILE_PATH?.trim();
  if (configuredProfilePath) {
    return isAbsolute(configuredProfilePath)
      ? configuredProfilePath
      : resolve(process.cwd(), "../..", configuredProfilePath);
  }

  const profileId = process.env.DOCMIND_CONNECTOR_PROFILE_ID?.trim();
  if (!profileId || !/^[a-zA-Z0-9_-]+$/.test(profileId)) return undefined;

  return resolve(
    process.cwd(),
    "../..",
    "deployments",
    profileId,
    "profile.yml",
  );
}

function connectorConfigurationRegistryPath(): string {
  const profilePath = connectorProfilePath();
  if (!profilePath) return defaultConnectorConfigurationRegistry;

  const profileRegistry = resolve(
    dirname(profilePath),
    "web/connector-configuration-extensions.ts",
  );
  return existsSync(profileRegistry)
    ? profileRegistry
    : defaultConnectorConfigurationRegistry;
}

const nextConfig: NextConfig = {
  output: "standalone",
  logging: {
    browserToTerminal: "warn",
    fetches: {
      fullUrl: false,
    },
    incomingRequests: {
      ignore: [/^\/_next\//, /^\/favicon[.]ico$/, /^\/api\/dev\/logs$/],
    },
  },
  webpack(config) {
    for (const resolverPlugin of config.resolve.plugins ?? []) {
      const plugin = resolverPlugin as {
        jsConfigPlugin?: boolean;
        paths?: Record<string, unknown>;
      };
      if (plugin.jsConfigPlugin) {
        delete plugin.paths?.[connectorConfigurationRegistryAlias];
      }
    }

    config.resolve.alias[`${connectorConfigurationRegistryAlias}$`] =
      connectorConfigurationRegistryPath();
    return config;
  },
};

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

export default withNextIntl(nextConfig);
