# Introduction #

Mostly these are acronyms.  Please feel free to add entries, even if you don't know what they are.  Someone else can come along and fill them in.

# Glossary #

<a href='Hidden comment: 
Each entry is a paragraph with the acronym in bold.  After the acronym use a space and colon and another space before the explanation.  Like this:

*ENTRY* : Explanation.

Separate each entry with a blank line (to make it a new paragraph).
'></a>

**anomaly** : (in the context of ccc-gistemp) An anomaly is the deviation of a monthly temperature from its climatology (the average value of that month's temperature over some reference period).  When producing zonal means ccc-gistemp uses a reference period of 1951 to 1980.

**ccc-gistemp** : Clear Climate Code GISTEMP.  This project; a reimplementation of GISTEMP.

**duplicate** : In GHCN version 2 a _duplicate_ is one of several records for the same station.  They arise because data for the a particular station may arrive via different sources having been processed (for QA for example) differently.

**GHCN** : [Global Historical Climate Network](http://www.ncdc.noaa.gov/oa/climate/ghcn-monthly/).  A database of "historical temperature, precipitation, and pressure data for thousands of land stations worldwide".  A primary source for ccc-gistemp and the largest source of temperature data used in the analysis.

**GISTEMP** : A historical temperature reconstruction made by NASA GISS.

**MCDW** : Monthly Climatic Data for the World.  A quality controlled publication of historical weather values.

**record** : A coherent set of data (monthly temperature values) gathered at a single location.  Because of differences in reporting procedures, computation of monthly means, and so on, a single station may have several records (in GHCN v2 these are called _duplicates_).

**station** : A location at which climate data (temperatures) are recorded.  Though the precise location of the equipment may move, the record as a whole may be regarded as coming from the same station.

**USCRN** : US Climate Reference Network. A set of modernized, ideally placed weather stations located in rural areas around the US.  (This contains daily and synoptic data since about the year 2000, it is not used by GISTEMP or ccc-gistemp).

**USHCN** : [United States Historical Climatology Network](http://cdiac.ornl.gov/epubs/ndp/ushcn/ushcn.html).  "a high quality data set of daily and monthly records of basic meteorological variables from 1218 observing stations across the 48 contiguous United States".  A primary source for ccc-gistemp, used in preference to GHCN over the contiguous US.

**zone** : (in ccc-gistemp but also sometimes elsewhere) A slice of the Earth taken parallel to the equator.  A zone is bounded above and below by lines of constant latitude.  In the final stages of analysis ccc-gistemp computes means over 8 zones and uses these to compute means for hemispheres and the globe.