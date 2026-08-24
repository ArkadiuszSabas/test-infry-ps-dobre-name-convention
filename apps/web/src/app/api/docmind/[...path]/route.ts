import { proxyDocmindApiRequest } from "@/lib/api/proxy-route";
import { getServerConfig } from "@/lib/config/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export const GET = proxyDocmindApiRequestWithServerConfig;
export const HEAD = proxyDocmindApiRequestWithServerConfig;
export const OPTIONS = proxyDocmindApiRequestWithServerConfig;
export const POST = proxyDocmindApiRequestWithServerConfig;
export const PUT = proxyDocmindApiRequestWithServerConfig;
export const PATCH = proxyDocmindApiRequestWithServerConfig;
export const DELETE = proxyDocmindApiRequestWithServerConfig;

function proxyDocmindApiRequestWithServerConfig(
  request: Request,
): Promise<Response> {
  return proxyDocmindApiRequest(request, getServerConfig());
}
