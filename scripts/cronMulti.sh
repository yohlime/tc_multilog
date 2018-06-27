WRKDIR=/home/modelgal/cron/ty_multilog
SCRIPTDIR=$WRKDIR/scripts
OUTDIR=/home/modelgal/data/tc/ty_multilog

cd $WRKDIR

MFILE=$(sed -n 1p info.txt)
JFILE=$(sed -n 2p info.txt)

MULTIDIR=output/multi
CSVDIR=output/csv
SHPDIR=output/shp

aria2c http://www.typhoon2000.ph/multi/data/$MFILE
aria2c https://metoc.ndbc.noaa.gov/ProductFeeds-portlet/img/jtwc/products/$JFILE

TCNAME=$(basename $MFILE .TXT) 
PFILE=""
[ "$(ls -A $CSVDIR)" ] && PFILE=$(ls -r $CSVDIR/*.csv | head -1)

if [ -s "$MFILE" ]; then
   d_str=$(sed -n 2p $MFILE | tr -d '()')
   d_utc=$(date --date="$d_str" -u +'%Y-%m-%d %H:%M:%S')
   d_loc=$(date --date="$d_str" +'%Y-%m-%d %H:%M:%S')
else
   d_utc=$(date -u +'%Y-%m-%d %H:%M:%S')
   d_loc=$(date +'%Y-%m-%d %H:%M:%S')
fi

read Yu mu du Hu Mu Su <<< ${d_utc//[-: ]/ }
read Y m d H M S <<< ${d_loc//[-: ]/ }

if [ -s "$MFILE" ]; then
   mv $MFILE $MULTIDIR/$(basename $MFILE .TXT)_$Y$m${d}_$H$M.txt
   MFILE=$MULTIDIR/$(basename $MFILE .TXT)_$Y$m${d}_$H$M.txt
fi

if [ -s "$JFILE" ]; then
   mv $JFILE $MULTIDIR/$(basename $JFILE .txt)_$Y$m${d}_$H$M.txt
   JFILE=$MULTIDIR/$(basename $JFILE .txt)_$Y$m${d}_$H$M.txt
fi

function makeleft() {
if [ -z ${2+x} ]; then
	ts=($(sed -n "/$1/,//p" $MFILE | tail -n+2 | cut -d\  -f1 | tr -d '()+[A-Za-z\-]'))
else
	ts=($(sed -n "/$1/,/$2/p" $MFILE | head -n-1 | tail -n+2 | cut -d\  -f1 | tr -d '()+[A-Za-z\-]'))
fi

tcnt=$(( ${#ts[*]} - 1 ))
for t in $(seq 0 $tcnt)
do
	tstr=${ts[t]}
	if [ $t -eq 0 ]; then
		do=$(date --date="$Yu-$mu-${tstr:0:2} ${tstr:2:2}:${tstr:4:2} UTC" +'%b %e %l %P' | tr -s " ")
		echo $1,$do
	else
		echo $1,$(date --date="$do $tstr hour" +'%b %e %l %P' | tr -s " ")
	fi
done
}

function makeright() {
if [ -z ${2+x} ]; then
	sed -n "/$1/,//p" $MFILE | tail -n+2 | cut -d\  -f2- | sed "s/[A-Za-z\-]*//g;s/\ /,/g"
else
	sed -n "/$1/,/$2/p" $MFILE | head -n-1 | tail -n+2 | cut -d\  -f2- | sed "s/[A-Za-z\-]*//g;s/\ /,/g"
fi
}

function getjtwc_radii() {
  dstr=$(sed '/WARNING POSITION/,/NEAR/!d' $JFILE | tail -1 | tr -s ' ' | cut -d\  -f2)
  dtstr=$(date -d "$d_utc" -u +'%Y-%m')
  dtstr="$dtstr-$(echo $dstr | cut -c-2) $(echo $dstr | cut -c3-4):00:00"
  
  ft=(24 36 72 96 120)
  
  dstr1=$(date -d "$dtstr $1 hours" -u +'%d%H00Z')
  dstr2=$(date -d "$dtstr $2 hours" -u +'%d%H00Z')
  temp=($(sed -n "/$dstr1/,/$dstr2/p" $JFILE | grep "KT WINDS\|NM NORTHEAST" | tr -d '[A-Za-z]\ \t\r\f'))
  for t in ${temp[@]}
  do
    rad[$(echo $t | cut -d\- -f1)]=$(echo $t | cut -d\- -f2 | sed 's/^0*//')
  done
  echo ,${rad[034]},${rad[050]},${rad[064]}
  unset rad
}

if [ -s "$JFILE" ]; then
   hArr=(0)
   hArr+=($(sed -n '/VALID AT/{p}' $JFILE | tr -d '[A-Za-z]\-\,\:\ \t\r\f'))

   tstr=$(sed -n '/WARNING POSITION/{n;p}' $JFILE | tr -d '[A-Za-z]\-\t\r\f' | tr -s ' ' | cut -d ' ' -f2)
   narr=${#hArr[@]}
   for i in $(seq 0 $(( narr-1 )))
   do
     if [ $i -eq 0 ]; then
       do=$(date --date="$Yu-$mu-${tstr:0:2} ${tstr:2:2}:${tstr:4:2} UTC" +'%b %e %l %P' | tr -s " ")
       echo JTWC,$do >> jleft.csv
     else
       echo JTWC,$(date --date="$do ${hArr[$i]} hour" +'%b %e %l %P' | tr -s " ") >> jleft.csv
     fi
   done


   sed -n '/WARNING POSITION/{n;p}' $JFILE | tr -d '[A-Za-z]\-\t\r\f' | tr -s ' ' | cut -d ' ' -f3- | tr ' ' ',' > jmid1.csv
   sed -n '/VALID AT/{n;p}' $JFILE | tr -d '[A-Za-z]\-\t\r\f' | tr -s ' ' | cut -d ' ' -f3- | tr ' ' ',' >> jmid1.csv

   sed -n '/MAX SUSTAINED WINDS -/{p}' $JFILE | cut -d - -f 2 | cut -d , -f1 | tr -d '[A-Za-z]\ \t\r\f' | sed 's/^0*//' > jmid2.csv

   paste -d, jmid1.csv jmid2.csv > jmid.csv

   narr=${#hArr[@]}
   for i in $(seq 0 $(( narr-1 )))
   do
     getjtwc_radii ${hArr[$i]} ${hArr[$(( i+1 ))]} | sed 's/,//' >> jright.csv
   done

   paste -d, jleft.csv jmid.csv > buff.csv
   paste -d, buff.csv jright.csv > jtwc.csv

else
   touch jtwc.csv
fi

if [ -s "$MFILE" ]; then
   CNAME=($(grep : $MFILE | tail -n+2 | tr -d :))
   CCNT=$(( ${#CNAME[@]} - 1 ))


   for i in $(seq 0 $CCNT)
   do
	  ii=$(( i + 1 ))
	  if [ ${CNAME[i]} != "JTWC" ]; then
		  makeleft ${CNAME[i]} ${CNAME[ii]} >> left.csv
		  makeright ${CNAME[i]} ${CNAME[ii]} >> right.csv
	  fi
   done
   paste -d, left.csv right.csv > other.csv

   Rscript 10min_2_1min.R
else
   touch other.csv
fi

touch mult.csv
cat jtwc.csv >> mult.csv
cat other.csv >> mult.csv

[[ -s mult.csv ]] && Rscript $SCRIPTDIR/compute.R

echo "Center,Date,Lat,Lon,Vmax,Cat,R63,R93,R119" >> $CSVDIR/${TCNAME}_$Y$m$d$H${M}_multilog.csv
if [ -n "$PFILE" ]; then
  RFILE=$SCRIPTDIR/appendprevJTWC.R
  echo "hello"
  sed -i "1 c prevFile='$PFILE'" $RFILE
  if [ -s jtwc.csv ];  then
     sed -i "2 c curDate='$(sed -n 1p jtwc.csv | cut -d, -f2)'" $RFILE
  else
     sed -i "2 c curDate=''" $RFILE
  fi
  Rscript $RFILE
  cat jprev.csv >> $CSVDIR/${TCNAME}_$Y$m$d$H${M}_multilog.csv
else
  touch $CSVDIR/${TCNAME}_$Y$m$d$H${M}_multilog.csv
fi

cat mult.csv >> $CSVDIR/${TCNAME}_$Y$m$d$H${M}_multilog.csv

cp SCRIPTDIR/csv.vrt .
cp $CSVDIR/${TCNAME}_$Y$m$d$H${M}_multilog.csv input.csv
ogr2ogr -f "ESRI Shapefile" . input.csv && ogr2ogr -f "ESRI Shapefile" . csv.vrt
mv output.* $SHPDIR/.
rename output ${TCNAME}_$Y$m$d$H${M}_multilog $SHPDIR/output.*


ASOF=$(date --date="1 hour ago" +'%_d%b%_I%P' | tr -d ' ')
FORUPDATE=$(date --date="3 hours" +'%_d%b%_I%P' | tr -d ' ')
zip multilog_asof${ASOF}_for$FORUPDATE.zip $CSVDIR/${TCNAME}_$Y$m$d$H${M}_multilog.csv $SHPDIR/${TCNAME}_$Y$m$d$H${M}_multilog.*
mv multilog_asof${ASOF}_for$FORUPDATE.zip $OUTDIR

rm -f *.csv *.dbf
