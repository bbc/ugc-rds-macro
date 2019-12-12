1: Single-AZ (Currently our database are deployed into a single-az)

Creating a DB snapshot on a Single-AZ DB instance leads to a brief I/O 
suspension. 

The I/O suspension can last a few seconds or minutes 
depending on the instance size and class of your DB instance. Multi-AZ 
DB instances are not affected by the I/O suspension because the backup 
is taken from the standby.

2: