import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080/api';
const PROXY_URL = process.env.PROXY_URL || 'http://localhost:5173/api';

test('TruthLens End-to-End System Integration Suite', async (t) => {
  const timestamp = Date.now();
  const testUser = {
    email: `e2e_analyst_${timestamp}@truthlens.test`,
    password: 'Password123!',
    fullName: 'E2E Test Analyst',
  };

  let authToken = '';
  let uploadedMediaId = '';

  await t.test('Workflow A: User Registration, Login, Profile, and Token Authentication', async () => {
    // 1. Register
    const regRes = await fetch(`${BACKEND_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testUser),
    });
    const regText = await regRes.text();
    assert.strictEqual(regRes.status, 201, `Registration should return 201 Created. Body: ${regText}`);
    const regData = JSON.parse(regText);
    assert.strictEqual(regData.message, 'Registration successful');
    assert.strictEqual(regData.email, testUser.email);

    // 2. Login
    const loginRes = await fetch(`${BACKEND_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: testUser.email, password: testUser.password }),
    });
    assert.strictEqual(loginRes.status, 200, 'Login should return 200 OK');
    const loginData = await loginRes.json();
    assert.ok(loginData.token, 'Login should return JWT token');
    authToken = loginData.token;

    // 3. Current User Profile via Spring Security JWT
    const profileRes = await fetch(`${BACKEND_URL}/users/me`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(profileRes.status, 200, 'Profile fetch should return 200 OK');
    const profileData = await profileRes.json();
    assert.strictEqual(profileData.email, testUser.email);
    assert.strictEqual(profileData.fullName, testUser.fullName);
    assert.ok(Array.isArray(profileData.roles) && profileData.roles.length > 0, 'User should have assigned roles');

    // 4. Test through Frontend Vite Proxy
    const proxyProfileRes = await fetch(`${PROXY_URL}/users/me`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(proxyProfileRes.status, 200, 'Vite Proxy to /api/users/me should return 200 OK');
    const proxyProfileData = await proxyProfileRes.json();
    assert.strictEqual(proxyProfileData.email, testUser.email);
  });

  await t.test('Workflow B: Media Upload, Hash/MIME Verification, and Image Forensic Analysis', async () => {
    // 1. Upload real image
    const sampleImagePath = path.resolve('frontend/src/assets/hero.png');
    assert.ok(fs.existsSync(sampleImagePath), 'Sample hero image must exist');
    const imageBytes = fs.readFileSync(sampleImagePath);

    const formData = new FormData();
    const fileBlob = new Blob([imageBytes], { type: 'image/png' });
    formData.append('file', fileBlob, 'hero.png');

    const uploadRes = await fetch(`${BACKEND_URL}/media/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}` },
      body: formData,
    });

    const uploadText = await uploadRes.text();
    assert.strictEqual(uploadRes.status, 201, `Upload should return 201 Created. Body: ${uploadText}`);
    const uploadData = JSON.parse(uploadText);
    assert.ok(uploadData.id, 'Upload must return media UUID');
    assert.strictEqual(uploadData.mediaType, 'IMAGE');
    assert.strictEqual(uploadData.mimeType, 'image/png');
    assert.ok(uploadData.sha256Hash, 'Upload must return calculated SHA-256 hash');
    uploadedMediaId = uploadData.id;

    // 2. Fetch Media Metadata
    const mediaRes = await fetch(`${BACKEND_URL}/media/${uploadedMediaId}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(mediaRes.status, 200, 'Media fetch should return 200 OK');
    const mediaData = await mediaRes.json();
    assert.strictEqual(mediaData.id, uploadedMediaId);
    assert.strictEqual(mediaData.sha256Hash, uploadData.sha256Hash);

    // 3. Module 03: Fingerprint & Duplicate Detection
    const fpRes = await fetch(`${BACKEND_URL}/media/${uploadedMediaId}/fingerprint`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(fpRes.status, 200, 'Fingerprint endpoint should return 200 OK');
    const fpData = await fpRes.json();
    assert.ok(fpData.sha256Hash, 'Fingerprint must contain sha256Hash');

    // 4. Module 04: Metadata Forensics
    const metaRes = await fetch(`${BACKEND_URL}/media/${uploadedMediaId}/metadata`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(metaRes.status, 200, 'Metadata endpoint should return 200 OK');
    const metaData = await metaRes.json();
    assert.strictEqual(metaData.mediaId, uploadedMediaId);

    // 5. Module 05: Image Authenticity Analysis (Spring Boot -> FastAPI AI/ML)
    const analysisRes = await fetch(`${BACKEND_URL}/media/${uploadedMediaId}/image-analysis`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(analysisRes.status, 200, 'Image analysis endpoint should return 200 OK');
    const analysisData = await analysisRes.json();
    assert.ok(typeof analysisData.aiProb === 'number', 'AI probability must be a valid number');
    assert.ok(typeof analysisData.manipulationProb === 'number', 'Manipulation probability must be a valid number');
    assert.ok(analysisData.authenticityAssessment, 'Authenticity assessment must be present');

    // 6. Forensic Evidence
    const evidenceRes = await fetch(`${BACKEND_URL}/media/${uploadedMediaId}/image-analysis/evidence`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(evidenceRes.status, 200, 'Image evidence endpoint should return 200 OK');
    const evidenceData = await evidenceRes.json();
    assert.ok(typeof evidenceData.copyMoveDetected === 'boolean', 'Evidence must include copyMoveDetected flag');
    assert.ok(typeof evidenceData.splicingDetected === 'boolean', 'Evidence must include splicingDetected flag');

    // 7. Visual Artifacts (ELA / Grad-CAM heatmap PNG stream)
    const elaRes = await fetch(`${BACKEND_URL}/media/${uploadedMediaId}/image-analysis/artifacts/ela`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(elaRes.status, 200, 'ELA artifact should stream with 200 OK');
    assert.strictEqual(elaRes.headers.get('content-type'), 'image/png');
    const elaBuffer = await elaRes.arrayBuffer();
    assert.ok(elaBuffer.byteLength > 0, 'ELA PNG artifact must have non-zero bytes');
  });

  await t.test('Workflow E: Claims & NLP Direct Text Extraction (Module 11)', async () => {
    const claimRequest = {
      text: 'Scientists at the World Health Organization confirmed a major discovery in renewable solar energy yesterday in Geneva.',
      sourceType: 'DIRECT_INPUT',
      language: 'en',
    };

    const claimRes = await fetch(`${BACKEND_URL}/claims/extract`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify(claimRequest),
    });

    assert.strictEqual(claimRes.status, 200, 'Direct text claim extraction should return 200 OK');
    const claimData = await claimRes.json();
    assert.ok(Array.isArray(claimData.claims), 'Claims should be an array');
    assert.ok(claimData.claims.length > 0, 'Should extract at least one claim');
    assert.ok(claimData.claims[0].claimText, 'Claim should have claimText');
    assert.ok(claimData.claims[0].claimType, 'Claim should have claimType');
    assert.ok(claimData.claims[0].entities, 'Claim should extract named entities');
  });

  await t.test('Workflow F: Dashboard User Media Fetch & Real Forensic State', async () => {
    const myMediaRes = await fetch(`${BACKEND_URL}/media/my`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(myMediaRes.status, 200, 'My media endpoint should return 200 OK');
    const myMedia = await myMediaRes.json();
    assert.ok(Array.isArray(myMedia), 'My media should return an array');
    assert.ok(myMedia.length >= 1, 'My media should contain the uploaded asset');
    const found = myMedia.find((m) => m.id === uploadedMediaId);
    assert.ok(found, 'Uploaded media ID must be present in user media list');
  });

  await t.test('Workflow G: Cases and Reports Backend Missing Status Verification', async () => {
    // Verify that /api/cases and /api/reports are indeed not implemented in backend (returns 500/404)
    // confirming our frontend fallback banner accurately reflects backend reality without fake data.
    const casesRes = await fetch(`${BACKEND_URL}/cases`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.ok(casesRes.status === 404 || casesRes.status === 500, `/api/cases should return error or 404/500 as M17 backend is pending. Received: ${casesRes.status}`);

    const reportsRes = await fetch(`${BACKEND_URL}/reports`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.ok(reportsRes.status === 404 || reportsRes.status === 500, `/api/reports should return error or 404/500 as M18 backend is pending. Received: ${reportsRes.status}`);
  });

  await t.test('Workflow A (Teardown): User Logout & Token Invalidation', async () => {
    const logoutRes = await fetch(`${BACKEND_URL}/auth/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}` },
    });
    assert.strictEqual(logoutRes.status, 200, 'Logout should return 200 OK');
    const logoutData = await logoutRes.json();
    assert.ok(logoutData.message.includes('revoked') || logoutData.message.includes('successful'));
  });
});
