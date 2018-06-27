prevFile='csv/TEMBIN_201712241200_multilog.csv'
curDate='Dec 24 2 pm'

pd <- read.csv(prevFile)
pd$date2 <- strptime(pd$Date,format="%b %e %l %p")

if (nchar(curDate) > 0) {
    od <- pd[pd$date2 < strptime(curDate,format="%b %e %l %p") & pd$Center == "JTWC",]
} else {
    od <- pd[pd$Center == "JTWC",]
}
write.table(od[,1:6],file="jprev.csv",sep=",",quote=F,na="",row.names=F,col.names=F)
q("no")
