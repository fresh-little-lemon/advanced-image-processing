# Verified source map (2026-10-19)

Source dataset: https://huggingface.co/datasets/freshlittlelemon/image-processing/tree/main

## Textbook identity and pagination
Verified cover, title and copyright: Rafael C. Gonzalez and Richard E. Woods, Digital Image Processing, Fourth Edition, **Global Edition**, Pearson Education Limited, ©2018, ISBN 978-1-292-22304-9. File 第4版原书(英文版,2018出版).pdf, 40,489,309 bytes, 1022 PDF pages. For this supplied file, PDF page = printed page + 2. Do not substitute US-edition pagination. Chapter/subheading citations below refer to this file. Subsection headings are unnumbered in the PDF; use section + heading, rather than asserting visible decimal subsection numbers.

## Condensed mapping
All slide numbers are 1-based physical slides. E = 传统图像增强202609.pptx (99 slides); P = Lecture02-1-Perception.ppt (29); S = Lecture02-2-Sampling.ppt (30); I = Lecture01-Intro-v30.ppt (56); W = 高级图像处理02.pptx (10).

| Topic | Confirmed PPT slides | Textbook printed / PDF pages |
|---|---|---|
| Image processing levels, acquisition/enhancement/restoration | I15,35,41–47 | §1.1 p18–19 / PDF20–21; §1.4 p41–44 / PDF43–46 |
| Eye structure, rods/cones, imaging | P3–7 | §2.1 p48–50 / PDF50–52 |
| Brightness adaptation, Weber ratio, Mach bands, simultaneous contrast | P8–19 | §2.1 p50–54 / PDF52–56 |
| Light and acquisition | P20–29 | §§2.2–2.3 p54–63 / PDF56–65 |
| Sampling, quantization, bit depth, resolution | S4–22 | §2.4 p63–77 / PDF65–79 |
| Interpolation/zoom | S23 | §2.4 p77–79 / PDF79–81 |
| Engineering resolution and capture-rate case | W10; S24–25 | Course applications; derive from sampling geometry, not a textbook exercise |
| Neighbors, adjacency, connectivity | S26–28 | §2.5 p79–82 / PDF81–84 |
| Distances (supplement) | No distinct slide located in supplied S deck | §2.5 p82–83 / PDF84–85 |
| Arithmetic, averaging, subtraction | S29; E29,31,34,54–58 | §2.6 p85–91 / PDF87–93 |
| Logic | S30 | §2.6 p92–96 / PDF94–98 |
| Enhancement vs restoration; point/neighborhood processing | E6–9 | §3.1 p120–122 / PDF122–124; §5.1 p318 / PDF320 |
| Negative / log / gamma | E10 / 11–12 / 13–16 | §3.2 p122–123 / PDF124–125; p124–125 / PDF126–127; p125–128 / PDF127–130 |
| Piecewise/contrast stretch, intensity slicing, bit planes | E17–19 / 20–23 /24–26 | §3.2 p128–130 / PDF130–132; p130–131 / PDF132–133; p131–133 / PDF133–135 |
| Histogram, equalization | E36–47 | §3.3 p133–140 / PDF135–142 |
| Histogram matching | E48–49 | §3.3 p140–149 / PDF142–151 |
| Local histograms / local statistics | E50–53; homework94 | §3.3 p149–150 / PDF151–152; p150–153 / PDF152–155 |
| CLAHE, BBHE, AMBE, optimal transport | E59–65 | Course extensions; not attributed to supplied textbook chapter |
| Masks, correlation/convolution, padding | E68–71 | §3.4 p153–164 / PDF155–166 (correlation/convolution p154–160 / PDF156–162) |
| Mean/weighted smoothing, Gaussian | E72–75 | §3.5 p164–174 / PDF166–176 |
| Order-statistic, median | E76–77 | §3.5 p174–175 / PDF176–177 |
| Derivatives / Laplacian | E78–84 | §3.6 p175–182 / PDF177–184 |
| Unsharp / highboost | E85–87 | §3.6 p182–184 / PDF184–186 |
| Gradient / Roberts / Sobel | E88–90 | §3.6 p184–188 / PDF186–190 |
| Combined enhancement | E91–95 | §3.8 p191–195 / PDF193–197 |
| Nagao edge-preserving filter | E96 | Lecture appendix, not a core chapter3 reference |

start.pptx contains six engineering problem-framing slides about dredging vessel monitoring, not additional enhancement formulas. W is text-bearing, not image-only.

## Brief genuine discrepancies to handle in study notes
1. E29 averaging code sets accumulator to original f, adds 50 noisy images, then divides by 50. Correct to a zero accumulator for 50 samples. Explain zero-mean independent noise assumptions; noise variance becomes sigma²/N, standard deviation sigma/sqrt(N).
2. E34 claims Python equivalence, but sigma12.9 is not equivalent to MATLAB normalized variance0.01 (nominal 8-bit sigma25.5 before clipping). Also separate x/y differences are not the same operator as E31 diagonal difference. Optional implementation note, not an exam priority.
3. E85 defines high boost as A f − blur. Textbook eq(3-56) p183 defines f + k(f−blur). They have different DC gain; do not silently equate A=k+1. State convention before numerical work.
4. E63/65 mean-preservation iff P(r≤m)=1−m/255 is an ideal continuous, exactly uniform subhistogram argument. It is not an unconditional discrete BBHE identity. Present as ideal-model extension, not a general theorem.
5. E40–41 continuous equalization uniformity does not imply discrete uniform output. E43 explicitly poses this issue; textbook p139 makes the distinction. Preserve this high-value exam caveat.
6. E94 calls local statistics §3.3.4; supplied Global Edition displays the heading within §3.3, p150–153. Cite the verified pages.
7. Spatial resolution depends on field of view and optical system; pixel dimensions alone (S16 wording) do not establish resolvable object size. W10 needs explicit assumptions on pixels across a crack, motion, line-scan versus area-scan and exposure.

All notes are paraphrases and bibliographic locators, not reproduced textbook content. Full local text extracts are for source checking only, not delivery.
