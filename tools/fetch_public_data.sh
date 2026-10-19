#!/usr/bin/env bash
# Fetch the public inputs for the full-size run into DATA_DIR.
#
# Everything comes from the Genome in a Bottle mirror on the AWS Registry of
# Open Data (giab.s3.amazonaws.com). The NCBI host ftp-trace.ncbi.nlm.nih.gov
# serves the same files but its robots.txt disallows every path, so scripts
# do not read from it.
#
# Reads are fetched by region with htslib range requests against the remote
# BAM index, so a 126 GB whole-genome BAM costs a few hundred MB of transfer.
# Run this on a node with internet access (a login or transfer node on a
# cluster); compute nodes usually have none, which is why it sits outside the
# Snakemake DAG.
#
# Usage: tools/fetch_public_data.sh [DATA_DIR]
# DATA_DIR defaults to $DATA_DIR from the environment, then resources/full,
# which is where config/config.yaml looks.
set -euo pipefail

DATA_DIR=${1:-${DATA_DIR:-resources/full}}
mkdir -p "$DATA_DIR"
# Absolute, because the script changes directory before writing outputs.
DATA_DIR=$(cd "$DATA_DIR" && pwd)
GIAB=https://giab.s3.amazonaws.com
SEED=42
# Two 2 Mb windows around the hereditary breast and ovarian cancer genes.
# BRCA2 sits at chr13:32.31-32.40 Mb and BRCA1 at chr17:43.04-43.13 Mb (GRCh38).
REGIONS=("chr13:32000001-34000000" "chr17:42500001-44500000")
CHROMS=(chr13 chr17)

AJ=data/AshkenazimTrio
BAM_HG002=$AJ/HG002_NA24385_son/NIST_HiSeq_HG002_Homogeneity-10953946/NHGRI_Illumina300X_AJtrio_novoalign_bams/HG002.GRCh38.60x.1.bam
BAM_HG003=$AJ/HG003_NA24149_father/NIST_HiSeq_HG003_Homogeneity-12389378/NHGRI_Illumina300X_AJtrio_novoalign_bams/HG003.GRCh38.60x.1.bam
BAM_HG004=$AJ/HG004_NA24143_mother/NIST_HiSeq_HG004_Homogeneity-14572558/NHGRI_Illumina300X_AJtrio_novoalign_bams/HG004.GRCh38.60x.1.bam
BAM_HG001=data/NA12878/NIST_NA12878_HG001_HiSeq_300x/NHGRI_Illumina300X_novoalign_bams/HG001.GRCh38_full_plus_hs38d1_analysis_set_minus_alts.300x.bam

# Target about 30x from each source: the trio BAMs are 60x, HG001 is 300x.
declare -A BAM=([HG001]=$BAM_HG001 [HG002]=$BAM_HG002 [HG003]=$BAM_HG003 [HG004]=$BAM_HG004)
declare -A FRACTION=([HG001]=0.1 [HG002]=0.5 [HG003]=0.5 [HG004]=0.5)

REL_AJ=release/AshkenazimTrio
declare -A TRUTH=(
  [HG001]=release/NA12878_HG001/NISTv4.2.1/GRCh38/HG001_GRCh38_1_22_v4.2.1_benchmark
  [HG002]=$REL_AJ/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark
  [HG003]=$REL_AJ/HG003_NA24149_father/NISTv4.2.1/GRCh38/HG003_GRCh38_1_22_v4.2.1_benchmark
  [HG004]=$REL_AJ/HG004_NA24143_mother/NISTv4.2.1/GRCh38/HG004_GRCh38_1_22_v4.2.1_benchmark
)
# HG001 ships one BED; the trio members ship a "noinconsistent" BED.
declare -A TRUTH_BED_SUFFIX=([HG001]=.bed [HG002]=_noinconsistent.bed [HG003]=_noinconsistent.bed [HG004]=_noinconsistent.bed)

STRAT=release/genome-stratifications/v3.3/GRCh38@all
STRAT_FILES=(
  LowComplexity/GRCh38_AllTandemRepeatsandHomopolymers_slop5.bed.gz
  SegmentalDuplications/GRCh38_segdups.bed.gz
  Mappability/GRCh38_lowmappabilityall.bed.gz
  Union/GRCh38_alldifficultregions.bed.gz
  Union/GRCh38_notinalldifficultregions.bed.gz
)
REF=release/references/GRCh38/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.gz

CURL=(curl -fsSL --retry 3 --retry-delay 5 -m 1800)
MANIFEST=$DATA_DIR/MANIFEST.tsv

log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >&2; }

record() {
  # record <local path> <source url> <how>
  local f=$1 url=$2 how=$3
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${f#"$DATA_DIR"/}" "$(stat -f %z "$f" 2>/dev/null || stat -c %s "$f")" \
    "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "$url" "$how" >>"$MANIFEST"
}

mkdir -p "$DATA_DIR"/{reads,reference,truth,stratifications,.htscache}
[[ -s $MANIFEST ]] || printf 'path\tbytes\tsha256\tfetched_utc\tsource\tmethod\n' >"$MANIFEST"
# htslib writes remote .bai/.tbi copies into the working directory.
cd "$DATA_DIR/.htscache"

printf '%s\t%s\t%s\n' chr13 32000000 34000000 chr17 42500000 44500000 >"$DATA_DIR/regions.bed"

if [[ ! -s $DATA_DIR/reference/GRCh38_chr13_chr17.fa ]]; then
  log "reference: ${CHROMS[*]} from the GIAB GRCh38 no-alt analysis set"
  samtools faidx "$GIAB/$REF" "${CHROMS[@]}" >"$DATA_DIR/reference/GRCh38_chr13_chr17.fa.tmp"
  mv "$DATA_DIR/reference/GRCh38_chr13_chr17.fa.tmp" "$DATA_DIR/reference/GRCh38_chr13_chr17.fa"
  record "$DATA_DIR/reference/GRCh38_chr13_chr17.fa" "$GIAB/$REF" "samtools faidx ${CHROMS[*]} (remote .fai and .gzi)"
fi

for s in HG001 HG002 HG003 HG004; do
  r1=$DATA_DIR/reads/${s}_R1.fastq.gz
  r2=$DATA_DIR/reads/${s}_R2.fastq.gz
  # samtools picks the output compression from the file suffix, so the
  # temporary names must still end in .fastq.gz.
  t1=$DATA_DIR/reads/${s}_R1.partial.fastq.gz
  t2=$DATA_DIR/reads/${s}_R2.partial.fastq.gz
  if [[ ! -s $r1 || ! -s $r2 ]]; then
    log "reads: $s fraction ${FRACTION[$s]} seed $SEED"
    # -F 0x900 drops secondary and supplementary records so each template is
    # written once; duplicates stay in so that markdup has real work to do.
    samtools view -u -F 0x900 --subsample "${FRACTION[$s]}" --subsample-seed "$SEED" \
      "$GIAB/${BAM[$s]}" "${REGIONS[@]}" |
      samtools collate -u -O - "$DATA_DIR/.htscache/collate_$s" |
      samtools fastq -n -0 /dev/null -s /dev/null \
        -1 "$t1" -2 "$t2" -c 6 - 2>"$DATA_DIR/reads/${s}.samtools_fastq.log"
    gzip -t "$t1" "$t2"
    mv "$t1" "$r1"
    mv "$t2" "$r2"
    how="samtools view -F 0x900 --subsample ${FRACTION[$s]} --subsample-seed $SEED ${REGIONS[*]} | collate | fastq (pairs only)"
    record "$r1" "$GIAB/${BAM[$s]}" "$how"
    record "$r2" "$GIAB/${BAM[$s]}" "$how"
  fi

  tv=$DATA_DIR/truth/${s}_v4.2.1_regions.vcf.gz
  if [[ ! -s $tv ]]; then
    log "truth VCF: $s"
    bcftools view -R "$DATA_DIR/regions.bed" -Oz -o "$tv" "$GIAB/${TRUTH[$s]}.vcf.gz"
    tabix -p vcf "$tv"
    record "$tv" "$GIAB/${TRUTH[$s]}.vcf.gz" "bcftools view -R regions.bed (remote .tbi)"
  fi

  tb=$DATA_DIR/truth/${s}_v4.2.1_benchmark.bed
  if [[ ! -s $tb ]]; then
    log "truth BED: $s"
    "${CURL[@]}" -o "$tb" "$GIAB/${TRUTH[$s]}${TRUTH_BED_SUFFIX[$s]}"
    record "$tb" "$GIAB/${TRUTH[$s]}${TRUTH_BED_SUFFIX[$s]}" "curl full file"
  fi
done

"${CURL[@]}" -o "$DATA_DIR/stratifications/GRCh38-genome-stratifications-md5s.txt" \
  "$GIAB/$STRAT/GRCh38-genome-stratifications-md5s.txt"
for f in "${STRAT_FILES[@]}"; do
  out=$DATA_DIR/stratifications/$(basename "$f")
  if [[ ! -s $out ]]; then
    log "stratification: $f"
    "${CURL[@]}" -o "$out" "$GIAB/$STRAT/$f"
    want=$(awk -v f="$f" '$2 == f {print $1}' "$DATA_DIR/stratifications/GRCh38-genome-stratifications-md5s.txt")
    got=$(md5 -q "$out" 2>/dev/null || md5sum "$out" | cut -d' ' -f1)
    if [[ $want != "$got" ]]; then
      log "MD5 mismatch for $f: published $want, got $got"
      exit 1
    fi
    record "$out" "$GIAB/$STRAT/$f" "curl full file; MD5 matches published list"
  fi
done

log "done; manifest at $MANIFEST"
