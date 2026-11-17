export async function verifyBlobSha256(file, digest, signal) {
  // Fetch checks the local representation on HTTP and HTTPS management pages.
  const local = URL.createObjectURL(file);
  try {
    const response = await fetch(local, { integrity: 'sha256-' + digest, signal });
    if (!response.ok) throw new Error('Could not verify file digest.');
    await response.arrayBuffer();
  } finally { URL.revokeObjectURL(local); }
}
