---
name: Health review
about: A by-hand health review (the monthly workflow opens one by itself, vt350#120)
title: Health review
labels: health-review
---

Run the unattended part and paste its report here:

```bash
python3 platform/health/health_review.py --repo dvystrcil/vt350 --out report.md \
  --dockerfile platform/kalisim/Dockerfile \
  --git-pin KALICO_SHA=https://github.com/KalicoCrew/kalico@main \
  --git-pin TOOLCHANGER_SHA=https://github.com/viesturz/klipper-toolchanger@main \
  --image-pin ghcr.io/kalicocrew/kalico:main \
  --run "bash platform/testing/check_test_tmp.sh" \
  --doc notes/status.md --doc cad/README.md --scripts cad/scripts
```

## Checked automatically
- [ ] CI: every workflow's newest run on `main` is not red
- [ ] Version drift: Kalico commit and image digest, klipper-toolchanger commit (amber = behind upstream)
- [ ] Manual run: `platform/testing/check_test_tmp.sh` passes on HEAD without FreeCAD
- [ ] Docs freshness: `notes/status.md`, `cad/README.md`
- [ ] Script hygiene: what's in `cad/scripts`

## For the owner
- [ ] CAD accuracy: the newest lite-N's checks and renders match the build plan
- [ ] Clash checks: the last sweep and refresh are clean, or each clash has an issue
- [ ] Renders: the newest renders show the current model
- [ ] Kalico simulation: printer.cfg limits still match the CAD (kalico-batch)
- [ ] Batch lane: the last few jobs finished and posted their comment
