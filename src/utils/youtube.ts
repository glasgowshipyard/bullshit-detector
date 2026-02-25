/**
 * YouTube URL detection and video ID extraction
 */

const YOUTUBE_REGEX =
  /(?:https?:\/\/)?(?:www\.)?(?:youtube|youtu|youtube-nocookie)\.(?:com|be)\/(?:watch\?v=|embed\/|v\/|live\/|.+\?v=)?([a-zA-Z0-9_-]{11})/;

/**
 * Returns the video ID if the query is a YouTube URL, otherwise null
 */
export function detectYoutubeUrl(query: string): string | null {
  const match = query.trim().match(YOUTUBE_REGEX);
  return match ? match[1] : null;
}

/**
 * Normalizes a YouTube video ID into a canonical watch URL
 */
export function toCanonicalUrl(videoId: string): string {
  return `https://www.youtube.com/watch?v=${videoId}`;
}
