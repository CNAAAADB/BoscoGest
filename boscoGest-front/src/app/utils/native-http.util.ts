import { Observable, from } from 'rxjs';
import { Capacitor, CapacitorHttp } from '@capacitor/core';

/**
 * Fetch a file as Blob, using CapacitorHttp.get() on native platforms
 * to bypass the broken XHR interceptor proxy for blob responses.
 * Falls back to the provided fallback observable on web.
 */
export function fetchBlobNative(
  url: string,
  webFallback: () => Observable<Blob>
): Observable<Blob> {
  if (!Capacitor.isNativePlatform()) {
    return webFallback();
  }

  return from(nativeFetchBlob(url));
}

async function nativeFetchBlob(url: string): Promise<Blob> {
  const token = localStorage.getItem('authToken');

  let response = await CapacitorHttp.get({
    url,
    responseType: 'blob',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  // CapacitorHttp does not follow redirects automatically.
  // If we get a 3xx with a Location header, follow it.
  if (response.status >= 300 && response.status < 400 && response.headers?.['location']) {
    const redirectUrl = response.headers['location'];
    response = await CapacitorHttp.get({
      url: redirectUrl,
      responseType: 'blob',
    });
  }

  const data = String(response.data);

  let base64Data: string;
  let contentType = 'application/octet-stream';

  // CapacitorHttp returns blob as data URL: "data:<mime>;base64,<base64data>"
  if (data.startsWith('data:')) {
    const commaIndex = data.indexOf(',');
    if (commaIndex !== -1) {
      const header = data.substring(5, commaIndex);
      const semicolonIndex = header.indexOf(';');
      contentType = semicolonIndex !== -1 ? header.substring(0, semicolonIndex) : header;
      base64Data = data.substring(commaIndex + 1);
    } else {
      base64Data = data;
    }
  } else {
    base64Data = data;
    contentType = response.headers?.['Content-Type']
      || response.headers?.['content-type']
      || 'application/octet-stream';
  }

  const binaryString = atob(base64Data);
  const byteArray = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    byteArray[i] = binaryString.charCodeAt(i);
  }

  return new Blob([byteArray], { type: contentType });
}
