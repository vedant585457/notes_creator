import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(1); // 4 GB RAM sandbox: one worker avoids compositor OOM
// Sandbox fallback: point REMOTION_BROWSER_EXECUTABLE at a Chromium binary (see README).
if (process.env.REMOTION_BROWSER_EXECUTABLE) {
  Config.setBrowserExecutable(process.env.REMOTION_BROWSER_EXECUTABLE);
}
