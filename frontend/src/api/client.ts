export const apiClient = async (url: string, options: RequestInit = {}) => {
  const defaultTenantId = "38ae0b79-3f96-4e4f-bf29-d2e2d74347ae";
  let tenantId = localStorage.getItem("tenant_id");
  if (!tenantId || tenantId === "null" || tenantId === "undefined" || tenantId.trim() === "") {
    tenantId = defaultTenantId;
  }

  const headers = new Headers(options.headers);
  headers.set("X-Tenant-ID", tenantId);

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let errorDetail = `Server error (${response.status})`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorDetail = errorData.detail;
      }
    } catch (e) {
      // Ignore if not JSON
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
};
