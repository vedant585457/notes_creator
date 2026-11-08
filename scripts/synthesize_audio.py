"""Deterministic, original SFX + music-bed synthesis for the Flag Hunters film.

Everything here is generated from math (seeded noise, sine/triangle oscillators),
so the output is owned by the project: no third-party samples, no licensing needed.
Run: python3 scripts/synthesize_audio.py
"""
import wave, os
import numpy as np

SR = 48000
OUT = os.path.join(os.path.dirname(__file__), '..', 'assets')
rng = np.random.default_rng(1337)  # seeded -> reproducible


def write_wav(path, x):
    x = np.clip(x, -1.0, 1.0)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    pcm = (x * 32767).astype('<i2')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def t_of(dur):
    return np.arange(int(SR * dur)) / SR


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (SR * tau))


def lowpass(x, a):
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y


def sfx_impact():
    d = 0.9; t = t_of(d)
    body = np.sin(2 * np.pi * (70 * np.exp(-t * 12) + 38) * t) * np.exp(-t * 5.5)
    noise = rng.standard_normal(len(t)) * np.exp(-t * 30) * 0.35
    return 0.5 * (body + noise)


def sfx_whoosh():
    d = 0.9; n = int(SR * d); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    y = np.zeros(n); acc = 0.0
    fc = 300 + 1500 * (t / d) ** 2  # rising filter cutoff
    for i in range(n):
        a = min(0.9, 2 * np.pi * fc[i] / SR)
        acc += a * (noise[i] - acc); y[i] = acc
    hp = y - np.concatenate([[0], y[:-1]]) * 0.97
    env = np.sin(np.pi * t / d) ** 1.6
    return 0.5 * hp * env / (np.max(np.abs(hp)) + 1e-9)


def sfx_tick():
    t = t_of(0.03)
    return 0.5 * np.sin(2 * np.pi * 2500 * t) * env_exp(len(t), 0.004)


def sfx_key():
    n = int(SR * 0.02); x = rng.standard_normal(n) * env_exp(n, 0.003)
    return 0.25 * lowpass(x, 0.5)


def sfx_blip():
    d = 0.09; t = t_of(d)
    f = 900 + 500 * t / d
    return 0.35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d)


def sfx_thud():
    d = 0.5; t = t_of(d)
    body = np.sin(2 * np.pi * (95 * np.exp(-t * 9) + 50) * t) * np.exp(-t * 8)
    noise = lowpass(rng.standard_normal(len(t)), 0.05) * np.exp(-t * 14)
    return 0.6 * (body + noise)


def sfx_riser():
    d = 3.0; t = t_of(d)
    f = 120 + 900 * (t / d) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    noise = lowpass(rng.standard_normal(len(t)), 0.08) * 0.6
    env = (t / d) ** 1.8
    return 0.45 * (tone + noise) * env


def sfx_chime():
    d = 2.6; t = t_of(d)
    out = np.zeros(len(t))
    for f, delay in [(880, 0.0), (1318.5, 0.12)]:
        tt = np.clip(t - delay, 0, None)
        out += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.2) * (t >= delay)
        out += 0.3 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 4) * (t >= delay)
    return 0.35 * out


def music_bed(total_s):
    """Slow A-minor pad, sub pulse at 72 BPM, sparse arpeggio. Chord changes every 8 s."""
    n = int(SR * total_s); t = np.arange(n) / SR
    chords = [  # midi notes
        [45, 52, 57, 60, 64],  # Am
        [41, 48, 53, 57, 60],  # F
        [48, 55, 60, 64, 67],  # C
        [43, 50, 55, 59, 62],  # G
    ]
    def mtof(m): return 440 * 2 ** ((m - 69) / 12)
    pad = np.zeros(n); arp = np.zeros(n); bass = np.zeros(n)
    beat = 60 / 72
    step = 8.0
    for k in range(int(total_s // step) + 1):
        s0, s1 = int(k * step * SR), min(n, int((k + 1) * step * SR))
        if s0 >= n: break
        seg_t = np.arange(s1 - s0) / SR
        ch = chords[k % 4]
        for m in ch:
            f = mtof(m)
            pad[s0:s1] += 0.035 * np.sin(2 * np.pi * f * seg_t) + 0.012 * np.sin(2 * np.pi * f * 2 * seg_t)
        # arpeggio: 8th notes, cycling chord tones (quiet)
        eighth = beat / 2
        for j in range(int(step / eighth)):
            a0 = s0 + int(j * eighth * SR)
            if a0 >= s1: break
            a1 = min(s1, a0 + int(0.35 * eighth * SR))
            f = mtof(ch[(j % 3) + 2] + 12)
            tt = np.arange(a1 - a0) / SR
            arp[a0:a1] += 0.018 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9)
        # sub pulse on quarter notes
        root = mtof(ch[0] - 12)
        for j in range(int(step / beat)):
            b0 = s0 + int(j * beat * SR)
            if b0 >= s1: break
            b1 = min(s1, b0 + int(0.22 * beat * SR))
            tt = np.arange(b1 - b0) / SR
            bass[b0:b1] += 0.18 * np.sin(2 * np.pi * root * tt) * np.exp(-tt * 6)
    # slow swell envelope
    swell = 0.7 + 0.3 * np.sin(2 * np.pi * t / 24)
    mix = (pad + arp) * swell + bass
    # gentle stereo spread via delayed copy
    left = mix
    right = np.concatenate([np.zeros(int(0.011 * SR)), mix[:-int(0.011 * SR)]])
    stereo = np.stack([left, right], axis=1)
    # fades
    fade = int(2 * SR)
    stereo[:fade] *= np.linspace(0, 1, fade)[:, None]
    stereo[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return 0.55 * stereo / (np.max(np.abs(stereo)) + 1e-9)


if __name__ == '__main__':
    sfx = {
        'impact': sfx_impact(), 'whoosh': sfx_whoosh(), 'tick': sfx_tick(),
        'key': sfx_key(), 'blip': sfx_blip(), 'thud': sfx_thud(),
        'riser': sfx_riser(), 'chime': sfx_chime(),
    }
    for name, x in sfx.items():
        write_wav(os.path.join(OUT, 'sfx', f'{name}.wav'), x * 0.8)
        print('sfx', name, round(len(x) / SR, 2), 's peak', round(float(np.max(np.abs(x))), 3))
    bed = music_bed(165.0)
    write_wav(os.path.join(OUT, 'music', 'bed_a_minor.wav'), bed)
    print('music bed', round(bed.shape[0] / SR, 2), 's')
