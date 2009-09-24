#!/usr/bin/perl -w

$id=0;
while(<>) {
    while(s/\t\?\t/\t?${id}?\t/) {
        $id++;
    }
    print;
}
