import { headers } from "next/headers";
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { buildBackendAuthHeaders } from "@/lib/backend-auth";
import { backendTraceHeaders, createProxyResponse } from "@/server/backend-api";

async function handleBranding(
  request: Request,
  { params }: { params: Promise<{ path?: string[] }> }
) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { path } = await params;
  const subPath = path && path.length ? `/${path.join("/")}` : "";
  const incomingUrl = new URL(request.url);
  const targetUrl = `${(process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "")}/branding${subPath}${incomingUrl.search}`;

  const authHeaders = {
    ...buildBackendAuthHeaders(session.user.id),
    ...(await backendTraceHeaders()),
  };

  const contentType = request.headers.get("content-type") || "";

  let body: any = undefined;
  const headersToSend: Record<string, string> = { ...authHeaders };

  if (request.method !== "GET" && request.method !== "HEAD") {
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData();
      body = formData;
    } else {
      body = await request.text();
      if (contentType) headersToSend["Content-Type"] = contentType;
    }
  }

  const upstream = await fetch(targetUrl, {
    method: request.method,
    headers: headersToSend,
    body,
    cache: "no-store",
    signal: request.signal,
  });

  return createProxyResponse(upstream);
}

export async function GET(request: Request, context: { params: Promise<{ path?: string[] }> }) {
  return handleBranding(request, context);
}

export async function POST(request: Request, context: { params: Promise<{ path?: string[] }> }) {
  return handleBranding(request, context);
}

export async function PATCH(request: Request, context: { params: Promise<{ path?: string[] }> }) {
  return handleBranding(request, context);
}

export async function DELETE(request: Request, context: { params: Promise<{ path?: string[] }> }) {
  return handleBranding(request, context);
}
