d<-read.csv("other.csv",header=F)
d$V5<-d$V5*1.14
write.table(d,file="other.csv",sep=",",quote=F,na="",row.names=F,col.names=F)
q("no")
