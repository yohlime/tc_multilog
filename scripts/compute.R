d<-read.csv("mult.csv",header=F)
d[,5]<-d[,5]*1.852
d[,dim(d)[2]+1]<-ifelse(d[,5]<=62,"TD",ifelse(d[,5]<=118,"TS",ifelse(d[,5]<=153,1,ifelse(d[,5]<=177,2,ifelse(d[,5]<=208,3,ifelse(d[,5]<=251,4,5))))))

if (ncol(d) >= 7) {
  d <-d[,c(1:5,ncol(d),6:(ncol(d)-1))]
  
  for (c in 7:ncol(d)) {
    d[,c]<-d[,c]*1.852
  }
}

write.table(d,file="mult.csv",sep=",",quote=F,na="",row.names=F,col.names=F)
q("no")
