#! /bin/bash

function help
{
    echo "scan.sh - usage:"
    echo "-a (append last scanned file to previously scanned file)"
    echo "-s 1 (adfsimplex), 2 (adfduplex), 3 (flatbed)"
    echo "-t 1 (text with OCR), 2 (text with orientation detection and OCR), 3 (graphics), 4 (fax, no OCR)"
    echo "-m 1 (color), 2 (grayscale)"
    echo "-o pdf, tiff, png, jpg (applicable to graphics mode only)"
}

append=false
source='Automatic Document Feeder'
adfmode='Simplex'
type='1'
mode='1'
output='pdf'

while getopts ":as:t:m:o:" opt; do
  case $opt in
    a)
      append=true
      ;;
    s)
      case $OPTARG in
        1)
          ;;
        2)
          adfmode='Duplex'
          ;;
        3)
          source='Flatbed'
          ;;
        *)
          echo "Invalid option for -s: $OPTARG"
          help
          exit 1
          ;;
       esac
      ;;
    t)
      case $OPTARG in
        1)
          ;;
        2)
          type='2'
          ;;
        3)
          type='3'
          ;;
        4)
          type='4'
          ;;
        *)
          echo "Invalid option for -t: $OPTARG"
          help
          exit 1
          ;;
       esac
      ;;
    m)
      case $OPTARG in
        1)
          ;;
        2)
          mode='2'
          ;;
        *)
          echo "Invalid option for -m: $OPTARG"
          help
          exit 1
          ;;
       esac
      ;;
    o)
      case $OPTARG in
        pdf)
          ;;
        tiff)
          output='tiff'
          ;;
        png)
          output='png'
          ;;
        jpg)
          output='jpg'
          ;;
        *)
          echo "Invalid option for -o: $OPTARG"
          help
          exit 1
          ;;
       esac
      ;;
  esac
done

echo $append
echo $source
echo $adfmode
echo $type
echo $mode
echo $output

if $append; then
  cd "somefolder"
  tmpfile="/tmp/$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c6).pdf"
  n=0
  for i in $(ls -t *-*-scan.pdf); do
    if [ $n -eq 0 ]; then
      orig="${i}"
    elif [ $n -eq 1 ]; then
      mv "${orig}" "${tmpfile}"
      pdfunite "${i}" "${tmpfile}" "${orig}"
      rm -f "${i}" "${tmpfile}"
      chown tim:tim "${orig}"
    else
      break
    fi
    ((n++));
  done
  exit 0
fi

. /usr/local/lib/job_pool.sh

# Sequential per-page processing function for OCR
function procpageocr
{
    # rotate even page numbers when scanning double-sided
    pagenum=${1##out}
    pagenum=$(echo $pagenum|sed 's/^0*//')
    echo "Starting job for page $pagenum"
    rem=$(( $pagenum % 2 ))
    if [ $rem -eq 0 -a "${adfmode}" = 'Duplex' ]; then
        nice -n 5 mogrify -rotate 180 "${1}.tif"
    fi
    nice -n 5 mogrify -level '6%,94%' -deskew '40%' -fuzz 2% -trim +repage -gravity 'NorthEast' -crop '2480x3508+0+0' +repage "${1}.tif"
    nice -n 5 textcleaner.sh -e none -o 10 "${1}.tif" "clean-${1}.tif"
    if [ $type -eq 2 ]; then
      echo "Detecting orientation for clean-${1}.tif"
      o=$(detect_orientation "clean-${1}.tif" 2>/dev/null | grep -o -P '(?<=^Orientation: )\d')
      echo "Orientation: ${o}"
      case "$o" in
        1)
          mogrify -rotate '270' +repage "clean-${1}.tif"
          mogrify -rotate '270' +repage "${1}.tif"
          ;;
        2)
          mogrify -rotate '180' +repage "clean-${1}.tif"
          mogrify -rotate '180' +repage "${1}.tif"
          ;;
        3)
          mogrify -rotate '90'  +repage "clean-${1}.tif"
          mogrify -rotate '90'  +repage "${1}.tif"
          ;;
      esac
    fi
    if [ $mode -eq 2 ]; then
        nice -n 5 convert "${1}.tif" -colorspace 'gray' -quality 65 "${1}.jpg"
    else
        nice -n 5 convert "${1}.tif" -quality 65 "${1}.jpg"
    fi
    nice -n 5 tesseract -l eng+nld "clean-${1}.tif" "${1}" hocr 2>/dev/null
    rm "${1}.tif" "clean-${1}.tif"
    if [ -f "${1}.html" ]; then
        mv "${1}.html" "${1}.hocr"
    fi
}

function procpagegfx
{
    # rotate even page numbers when scanning double-sided
    pagenum=${1##out}
    pagenum=$(echo $pagenum|sed 's/^0*//')
    echo "Starting gfx job for page $pagenum"
    rem=$(( $pagenum % 2 ))
    if [ $rem -eq 0 -a "$adfmode" = 'Duplex' ]; then
        nice -n 5 mogrify -rotate 180 "${1}.tif"
    fi
    nice -n 5 mogrify -level '6%,94%' -deskew '40%' -fuzz 2% -trim +repage -gravity 'NorthEast' -crop '2480x3508+0+0' +repage "${1}.tif"
    if [ $mode -eq 2 ]; then
        nice -n 5 mogrify "${1}.tif" -colorspace 'gray'
    fi
    case $output in
        tiff)
          dst="${dst}${1}.tif"
          mv "${1}.tif" "${dst}"
          chown tim:tim "${dst}"
        ;;
        png)
          optipng -o1 "${1}.tif"
          rm "${1}.tif"
          dst="${dst}${1}.png"

          mv "${1}.png" "${dst}"
          chown tim:tim "${dst}"
          ;;
        pdf)
          optipng -o1 "${1}.tif"
          rm "${1}.tif"
          ;;
        jpg)
          convert "${1}.tif" -quality 95 -compress jpeg "${1}.jpg"
          rm "${1}.tif"
          dst="${dst}${1}.jpg"
          mv "${1}.jpg" "${dst}"
          chown tim:tim "${dst}"
          ;;
    esac
}


dstdir="/somefolder"
tmpdir="/tmp/pdf-ocr/$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c6)"
if [ -z "$SANE_DEFAULT_DEVICE" ] ; then export SANE_DEFAULT_DEVICE="$(cat /etc/scanner)"; fi
if [ ! -d "$tmpdir" ]; then mkdir -p "$tmpdir"; fi

cd "$tmpdir"

dst="${dstdir}/$(date +'%Y%m%d-%H%M%S')-"

# setup scanner device

# step 1, scan
if [ "$source" = 'Flatbed' ]; then
   (scanimage --mode Color --resolution 300dpi        --source 'Flatbed' --format=tiff > tmp.tif; mv tmp.tif out01.tif) &
elif [ "$adfmode" = 'Duplex' ]; then
    scanimage --mode Color --resolution 300dpi -y 300 --source 'Automatic Document Feeder' --adf-mode 'Duplex' --batch=out%02d.tif --format=tiff &
else
    scanimage --mode Color --resolution 300dpi -y 300 --source 'Automatic Document Feeder'                     --batch=out%02d.tif --format=tiff &
fi

scanpid=$!

job_pool_init $(nproc) 0

case $type in
  [1-2])
    pgsscanned=1
    tmpstr="out0"
    sleep 20
    while [ -d "/proc/${scanpid}" ]; do
        if [ -f "$tmpstr$pgsscanned.tif" ]; then
            job_pool_run procpageocr "$tmpstr$pgsscanned"
            (( pgsscanned++ ))
            if [ $pgsscanned -eq 10 ]; then tmpstr="out"; fi
            sleep 10
        else
            sleep 1
        fi
    done

    if [ -f "$tmpstr$pgsscanned.tif" ]; then
        job_pool_run procpageocr "$tmpstr$pgsscanned"
    fi
    job_pool_wait
    hocr-pdf . > "out.pdf"
    dst="${dst}scan.pdf"
    mv "out.pdf" "${dst}"
    #chown tim:tim "${dst}"
    ;;
  3)
    pgsscanned=1
    tmpstr="out0"
    sleep 20
    while [ -d "/proc/${scanpid}" ]; do
        if [ -f "${tmpstr}${pgsscanned}.tif" ]; then
            job_pool_run procpagegfx "${tmpstr}${pgsscanned}"
            (( pgsscanned++ ))
            if [ $pgsscanned -eq 10 ]; then tmpstr="out"; fi
            sleep 10
        else
            sleep 1
        fi
    done

    if [ -f "${tmpstr}${pgsscanned}.tif" ]; then
        job_pool_run procpagegfx "${tmpstr}${pgsscanned}"
    fi
    job_pool_wait
    if [ $output = 'pdf' ]; then
	convert *.png +repage -density 72 -page A4 out.pdf
	dst="${dst}gfx.pdf"
	mv "out.pdf" "${dst}"
	#chown tim:tim "${dst}"
    fi
    ;;
  4)
    wait $scanpid
    convert *.tif -deskew '40%' -fuzz '2%' -trim +repage -gravity 'NorthEast' -crop '2480x3508+0+0' +repage - | convert - -density 204x196 -units PixelsPerInch -resize '1728x2290!' -threshold 60% -type bilevel -compress Group4 +profile "*" out.pdf
    dst="${dst}fax.pdf"
    mv "out.pdf" "${dst}"
    #chown tim:tim "${dst}"
    ;;
esac

job_pool_shutdown
echo "job_pool_nerrors: ${job_pool_nerrors}"

echo "All jobs done, output is ${dst}"
echo "Cleaning up."
rm *
cd "$OLDPWD"
rmdir "$tmpdir"
