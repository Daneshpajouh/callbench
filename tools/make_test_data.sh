#!/usr/bin/env bash
# Build the bundled test data in .tests/data from a finished full-size run.
#
# The test genome is a 200 kb slice of chr17 (GRCh38 chr17:42,950,001-43,150,000,
# which holds BRCA1) stored as a contig still called chr17, so every position in
# the test data is the GRCh38 position minus 42,950,000. Truth VCF, truth BED,
# stratification BEDs and the ClinVar subset are shifted by the same offset.
# Reads are the HG002 pairs that the full run aligned inside the slice.
#
# Usage: tools/make_test_data.sh [FULL_RESULTS_DIR] [FULL_DATA_DIR]
set -euo pipefail

RESULTS=${1:-results}
DATA=${2:-resources/full}
OUT=.tests/integration/data
CHROM=chr17
START=42950000 # 0-based start of the slice
END=43150000
LEN=$((END - START))
SLICE="$CHROM:$((START + 1))-$END"
SAMPLE=HG002

mkdir -p "$OUT"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Reference: the slice under the original contig name.
samtools faidx "$DATA/reference/GRCh38_chr13_chr17.fa" "$SLICE" |
  sed "1s/.*/>$CHROM/" >"$OUT/genome.fa"

# Reads: properly placed pairs inside the slice, written back to FASTQ.
samtools view -u -F 0x900 "$RESULTS/bam/$SAMPLE.markdup.bam" "$SLICE" |
  samtools collate -u -O - "$tmp/collate" |
  samtools fastq -n -0 /dev/null -s /dev/null -c 9 \
    -1 "$OUT/${SAMPLE}_R1.fastq.gz" -2 "$OUT/${SAMPLE}_R2.fastq.gz" -

# shift_vcf <in.vcf.gz> <region> <contig name in output> <out.vcf.gz>
# Keeps records that end inside the slice and rewrites the contig header.
shift_vcf() {
  local in=$1 region=$2 name=$3 out=$4
  bcftools view -r "$region" "$in" |
    awk -v s="$START" -v len="$LEN" -v name="$name" 'BEGIN { OFS = "\t" }
      /^##contig=/ { next }
      /^#CHROM/ { print "##contig=<ID=" name ",length=" len ">"; print; next }
      /^#/ { print; next }
      { $1 = name; $2 = $2 - s; if ($2 >= 1 && $2 + length($4) - 1 <= len) print }' |
    bgzip -c >"$out"
  tabix -f -p vcf "$out"
}

shift_bed() {
  # shift_bed <in.bed[.gz]> <contig> <out.bed>
  local in=$1 name=$2 out=$3
  { if [[ $in == *.gz ]]; then gzip -cd "$in"; else cat "$in"; fi; } |
    awk -v c="$name" -v s="$START" -v e="$END" 'BEGIN { OFS = "\t" }
      $1 == c && $3 > s && $2 < e {
        a = ($2 < s ? s : $2) - s; b = ($3 > e ? e : $3) - s; print c, a, b }' >"$out"
}

shift_vcf "$DATA/truth/${SAMPLE}_v4.2.1_regions.vcf.gz" "$SLICE" "$CHROM" "$OUT/${SAMPLE}_truth.vcf.gz"
shift_bed "$DATA/truth/${SAMPLE}_v4.2.1_benchmark.bed" "$CHROM" "$OUT/${SAMPLE}_truth.bed"
for f in GRCh38_AllTandemRepeatsandHomopolymers_slop5 GRCh38_segdups \
  GRCh38_lowmappabilityall GRCh38_alldifficultregions GRCh38_notinalldifficultregions; do
  shift_bed "$DATA/stratifications/$f.bed.gz" "$CHROM" "$OUT/$f.bed"
done
# ClinVar keeps its own contig naming (17, not chr17) so the rename step in the
# workflow is exercised by the test run.
shift_vcf "$DATA/clinvar/clinvar.vcf.gz" "17:$((START + 1))-$END" 17 "$OUT/clinvar.vcf.gz"

# Evaluate 10 kb inside each end of the slice.
printf '%s\t%s\t%s\n' "$CHROM" 10000 190000 >"$OUT/regions.bed"

ls -l "$OUT"
