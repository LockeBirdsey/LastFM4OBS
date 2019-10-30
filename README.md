# LastFM4OBS
LastFM4OBS is a tool used to get the more recently played last.fm track and store details into a text file and the album art. 
Somewhat configurable using a config file. Created to show now playing information on a stream created in OBS.
Multiple music sources made this is a requirement.

# Configuration
The `config.ini` file has two categories of options, namely, `LOCAL`, and `last.fm`
## `LOCAL`
`LOCAL` considers how the data where and how the Last.FM data is stored
`directory`: Select the directory where you'd like the Last.FM information to be stored
`format`: The format in which you'd like the textual information displayed. The format options are:

|Option|Description|
|---|---|
|%%TRACK|Track name|
|%%ARTIST|Artist name|
|%%ALBUM| Album name|
|\\\n | Newline character|
|\\\t | Tab character|

## `last.fm`
The `last.fm` category only considers which username is to be examined
`username`: The id of the user who you want to get Last.FM recently played data for (most likely your own account)


# Issues
There are several known issues:
* Occasionally Last.fm will return bad information even if it displayed fine on the last.fm website. I'm investigating how to fix this
* When using images with OBS, sometimes the image won't display. This is due to OBS's refreshing time when an image is updated
* Some songs are just not listed on last.fm and will not be displayed. An error will instead be logged

Any other issues please submit a bug request

# Enhancements
Several features coming soon:
* More configurable config file
* Better error handling
* Display more music data

![unknownalbumplaceholder.png](:/4c775f6e5b474812acafbd2d29fae3be)

