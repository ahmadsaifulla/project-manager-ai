export const apiClient = async (url: string, options: RequestInit = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': '38ae0b79-3f96-4e4f-bf29-d2e2d74347ae',
    ...options.headers,
  };

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
