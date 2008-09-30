c   To read the  oi SST version 2
c    and the masks.
c
c
      parameter (im=360,jm=180,ioff=im/2)
      parameter (iyrbeg=1880,iyreo=3003, nymax=15)
      parameter (monx=12*(iyreo-iyrbeg+1))
c
c   i is longitude index (values 1 to im)
c   j is the latitude index (values 1 to jm)
c
      real*4 sst(im,jm,12*nymax)
c
c   sst is the input SST real*2 array
c    (values are degrees C)
c
      integer info(8)
c
c   ls is the land/sea array not needed - built into climatology
c
      real to(monx)
      real clim(im,jm,12)
c
c   rsst is the reconstructed SST mean in degrees C
c   Read the EOF reconstruction area mask (unit 4)
c
      character*80 filei/
     *  'input_files/oiv2mon.yyyymm'/,line,title
      ny=index(filei,'yyyy')
      title(1:40)= 'Monthly Sea Surface Temperature anom (C)'
      title(41:80)=' Had: 1880-11/1981, oi2: 12/1981-mm/yyyy'
      info(1)=1
      info(2)=1
      info(3)=6
      info(4)=0  ! will be changed later
      info(5)=0  ! will be changed later
      info(6)=iyrbeg
      info(7)=9999
      info(8)=-9999

      open(1,file='input_files/SBBX.HadR2',form='unformatted')
      read(1) info,title
      bad=info(7)
      mnow=info(1)
      info(1)=1  ! input is trimmed, output is NOT trimmed/reorganized
c     info(4)=monx
c     info(5)=monx+4
      if(info(6).ne.iyrbeg) then
        write(*,*) 'iyrbeg-new',iyrbeg,' iyrbeg-old',info(6)
        stop 'iyrbeg inconsistent'
      end if
      write(*,*) 'SBBX.HadR2 opened'
      open(24,file='input_files/SBBX_LtSN.LnWE.dat',form='unformatted')

      open(14,file='input_files/oisstv2_mod4.clim',
     *        form='unformatted')
      read(14) line,clim
      close (14)
c
c   Read in the SST data for recent years (unit 11)
c
      call getarg(1,line)
      read(line,*) iyr1
      if(iyr1.lt.iyrbeg) then
        write(*,*) 'iyr1=',iyr1,' cannot be less than',iyrbeg
        stop 'arg 1 off'
      end if
      call getarg(2,line)
      read(line,*) iyrl
      if(iyrl.lt.iyr1.or.iyrl.gt.iyreo) then
        write(*,*) 'iyrl=',iyrl,' must be between',iyr1,' and',iyreo
        stop 'arg 2 off'
      end if
      if(info(4).lt.12*(iyrl+1-iyrbeg)) info(4)=12*(iyrl+1-iyrbeg)
      info(5)=info(4)+4  ! output has old, not trimmed format

      do 100 iyr=iyr1,min(iyrl,iyr1+nymax-1)
      do 90 mon=1,12
      write(filei(ny:ny+5),'(I4.4,I2.2)') iyr,mon
      write(*,*) 'trying to read ',filei(1:70)
      open(11,form='unformatted',file=filei,err=110)
      read(11) iyr0,imo
      iyre=iyr
      moe=mon
      if(iyr.ne.iyr0) write(*,*) 'years not ok',iyr,iyr0
      if(mon.ne.imo) write(*,*) 'months not ok',mon,imo
c
c   iyr is year (value 1950 to 1992)
c   imo is month (value 1 to 12)
c
      read(11) ((sst(i,j,12*(iyr-iyr1)+mon),i=1,im),j=1,jm)
   90 close (11)
  100 continue
  110 open(2,file='SBBX.HadR2.upd',form='unformatted')
      title(41:80)=' Had: 1880-11/1981, oi2: 12/1981-mm/yyyy'
      write(title(74:80),'(I2,''/'',I4)') moe,iyre
      write(2) info,title
c****
c**** Interpolate to Sergei's subbox grid
c****
      moff=(iyr1-iyrbeg)*12
      do 500 n=1,8000
      do 200 m=1,monx
  200 to(m)=bad
      call sread(1,to,mnow,lts,ltn,lnw,lne,mnext)
      mnow=mnext
      js=(18001+(lts+9000)*jm)/18000
      jn=(17999+(ltn+9000)*jm)/18000
      iw=(36001+(lnw+18000)*im)/36000+ioff
      ie=(35999+(lne+18000)*im)/36000+ioff
      if(ie.gt.im) then
         iw=iw-im
         ie=ie-im
      end if
      if(iw.gt.im) stop 'iw>im'
      if(ie.gt.im) stop 'ie>im'
      if(iw.lt.1) stop 'iw<1'
      if(ie.lt.1) stop 'ie<1'


      do 220 m=1,12*(iyre-iyr1)+moe
      month=mod(m-1,12)+1
      kt=0
      ts=0.
      do 210 j=js,jn
      do 210 i=iw,ie
      if(sst(i,j,m).le.-1.77.or.clim(i,j,month).eq.bad) go to 210
      kt=kt+1
      ts=ts+(sst(i,j,m)-clim(i,j,month))
  210 continue
        to(m+moff)=bad
        if(kt.gt.0) to(m+moff)=ts/kt
  220 continue
      do 230 m=(iyre-iyrbeg)*12+moe+1,info(4)
  230 to(m)=bad

      write(2) (to(i),i=1,info(4)),lts,ltn,lnw,lne ! old arr. untrimmed
  500 continue
      stop
      end

      subroutine sread(in,a,na,lts,ltn,lnw,lne,mnext)
      real a(na)
      integer info(7)
      read(in) mnext,lts,ltn,lnw,lne,x,x,x,a
      return
      end
