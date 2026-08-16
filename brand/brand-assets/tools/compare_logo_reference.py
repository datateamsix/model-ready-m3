#!/usr/bin/env python3
"""Reference comparison helper for PreM3 logo exports.
Usage: python compare_logo_reference.py candidate.png [reference.png]
This is a QA aid, not a substitute for design approval.
"""
from PIL import Image, ImageChops, ImageStat
import sys
from pathlib import Path

candidate=Path(sys.argv[1])
reference=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).parents[1]/'reference'/'prem3-approved-primary-logo-reference.png'
a=Image.open(reference).convert('RGB')
b=Image.open(candidate).convert('RGB').resize(a.size, Image.Resampling.LANCZOS)
d=ImageChops.difference(a,b)
stat=ImageStat.Stat(d)
rms=(sum(v*v for v in stat.rms)/3)**0.5
out=candidate.with_name(candidate.stem+'-diff.png')
d.save(out)
print(f'Reference: {reference}')
print(f'Candidate: {candidate}')
print(f'Compared at: {a.size[0]}x{a.size[1]}')
print(f'RMS pixel difference: {rms:.2f} (lower is closer; rasterization differences are expected)')
print(f'Diff image: {out}')
