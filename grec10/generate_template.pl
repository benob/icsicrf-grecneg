#!/usr/bin/perl -w

$num = shift;
for $id(1 .. $num - 2)
{
	print "U$id\%x[0,$id]\n";
	print "U$id\%x[-1,$id]\n";
	print "U$id\%x[-1,$id]/%x[0,$id]\n";
	#print "U$id\%x[1,$id]\n";
	print "B$id\%x[0,$id]\n";
	#print "B$id\%x[-1,$id]\n";
	#print "B$id\%x[1,$id]\n";
	#print "B$id\%x[0,$id]/\%x[-1,$id]\n";
}

print "B\n"
