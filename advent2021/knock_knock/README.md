# Credits

Thanks to [Steven](https://twitter.com/StevenVanAcker) for making this challenge!

This challenge was for the ninth day (December 15th) of the Advent CTF.

# Table of contents
1. [Starting off](#starting-off)
2. [Examining the server](#examining-the-server)
3. [Acquiring songs](#acquiring-songs)
4. [Caroling](#caroling)

# Starting off

We're presented with a command to run the challenge which presents us with the following:

```console
$ nc knockknock.advent2021.overthewire.org 25000
==[ Door 25000 ]==
asfdsa
That is not what I want to hear (I wanted 'knock knock')

$ nc knockknock.advent2021.overthewire.org 25000
==[ Door 25000 ]==
knock knock
Sing me this song...
O Tannenbaum, o Tannenbaum,
bd51ca6a2101bc04b469bab3a31a0d3fd32098d5cd118fa7dee3841c9c1a8650
```

We're also given the [source code](source/server.py) of the server code.

Note: the server code may be a _bit_ different that what was provided in the challenge.
The challenge is now offline and I didn't save a local copy of it, so there's a chance that when I tried to remove my edits that I forgot something.

Looks like we'll need to sing some songs to complete this challenge.
How festive!

# Examining the server

Looking closer into the guts of the server, we find that this challenge is pretty straightforward and will just require some programming.
In particular, we find:
- The flag is sent to us if we provide the correct lyrics for a song
- The song we have to provide lyrics for is randomly chosen (from a song list we do not know)
- Lyrics are given to the serevr one line at a time **and** to a random port (which we also don't know)
  - Sending lyrics to the wrong port resets the song / challenge
- The server provides us a SHA256 hash of the currently expected song lyric *and* the port we need to contact next
- The first lyric we have to send is always "knock knock"

In addition, since we're given the source code for this challenge, we can create our [own server instance](source/amended.py) to help with debugging.
Our instance can print values, provide a smaller port range, and provide us with a known flag so that we can validate.

# Acquiring songs

We don't know the _precise_ lyrics for most holiday songs, but [this website](https://www.41051.com/xmaslyrics/) does.
We can use the lyrics from the various songs on this page to populate what songs we'll need.

In addition, we can connect to the server and see the initial lyrics to the requested song to help us populate a list of songs that are being used.

# Caroling

Taking the above information and putting it all together, we get to a solution pretty easily.
Our approach:
1. Acquire a handful (only a few) of lyrics to songs we know the server is requesting us to "sing"
2. Contact the server initially with "knock knock" and use the return lyric to determine the desired song
3. If the requested song is not in our "song database," re-connect and go back to step 2
4. Using the SHA256 hash and our song lyrics, determine which port to contact
5. Send the next lyric of the song to the server
6. Repeat steps 4 and 5 until we finish the lyrics
7. If the server responds with a flag, we're good. If not, return to step 2

Our approach will be a little sloppy.
Instead of indexing _all_ the songs that are being requested, we'll only catalog a few songs and instead retry until one of our songs is randomly selected.
We can start up our exploit and go make some dinner; when we come back in a bit, we should find that we have our flag.

```console
$ ./exploit.py
......................
Close, but no flag
...........................
Close, but no flag
......................
Close, but no flag
......................
Close, but no flag
............
Close, but no flag
............
Close, but no flag
................
Close, but no flag
............
Flag: So beautiful, here is something for your trouble: <I_forgot_to_write_down_this_flag>
```

I unfortunately forgot to write down the flag (and the servers are currently down with no VM image / offline way to play), so you'll have to trust that I finished this challenge.
You can try locally to verify for yourself.
