#!/usr/bin/env perl

use strict;
use warnings;

my $input = $ARGV[0];
my $index = 0;

open INPUT, "<$input"
    or die "can't open $input for reading: $!\n";

foreach my $line (<INPUT>) {
    chomp $line;

    next if $line =~ /^\s*$/;
    next if $line =~ /^(?:Style|Format|\[)/;

    if ($line =~ /^Dialogue:/) {
        $index++;

        my @data = split /,/, $line;
        my ($start, $end) = @data[1,2];

        $start = ssatime2srt2time($start);
        $end   = ssatime2srt2time($end);

        my $text = $data[-1];
        $text =~ s/^\s*(?:“|")//;
        $text =~ s/(?:”|")\s*$//;

        print "\n$index\n$start --> $end\n$text\n";
    }
    else {
        my $text = $line;
        $text =~ s/^\s*(?:“|")//;
        $text =~ s/(?:”|")\s*$//;

        print "$text\n";
    }
}

close INPUT;

sub ssatime2srt2time {
    my $input = shift;
    $input =~ s/\s*$//;
    my @data = split /(?::|\.)/, $input;
    return sprintf "%02d:$data[1]:$data[2],$data[3]0", $data[0];
}
