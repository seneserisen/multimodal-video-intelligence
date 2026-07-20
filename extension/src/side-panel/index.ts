import { isExtensionMessage } from "../shared/messages";

const status = document.querySelector<HTMLParagraphElement>("#status");
const metadata = document.querySelector<HTMLPreElement>("#metadata");

async function inspect(): Promise<void> {
  if (status === null || metadata === null) return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id === undefined || tab.url === undefined) {
    status.textContent = "No readable active tab.";
    return;
  }
  try {
    const response: unknown = await chrome.tabs.sendMessage(tab.id, { type: "REQUEST_MEDIA_METADATA" });
    if (!isExtensionMessage(response)) throw new Error("Invalid content-script response");
    if (response.type === "MEDIA_METADATA") {
      status.textContent = `${response.platform}: ${String(response.videos.length)} visible-page video element(s)`;
      metadata.textContent = JSON.stringify(response.videos, null, 2);
    } else {
      status.textContent = "This platform is not supported.";
    }
  } catch {
    status.textContent = "Open a supported YouTube, Instagram, or TikTok page.";
  }
}

void inspect();
