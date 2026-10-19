# Print a chunk BED's single interval as a padded region, chrom:start-end,
# in the 0-based, end-exclusive form that freebayes --region takes.
# Usage: awk -v pad=1000 -f pad_region.awk genome.fa.fai chunk.bed
# The start is clamped at 0 and the end at the contig length from the .fai.
NR == FNR { len[$1] = $2; next }
/^(#|track|browser)/ || NF < 3 { next }
{
    if (!($1 in len)) { print "pad_region: contig " $1 " not in the .fai" > "/dev/stderr"; exit 1 }
    s = $2 - pad; if (s < 0) s = 0
    e = $3 + pad; if (e > len[$1]) e = len[$1]
    print $1 ":" s "-" e
    n++
}
END { if (n != 1) { print "pad_region: expected one interval, found " n + 0 > "/dev/stderr"; exit 1 } }
