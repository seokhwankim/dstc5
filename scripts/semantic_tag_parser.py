from HTMLParser import HTMLParser, HTMLParseError


class SemanticTagParser(HTMLParser):
    def __init__(self, chr_mode=True):
        self.reset()
        HTMLParser.__init__(self)
        self.__chr_mode = chr_mode

    def reset(self):
        self.__word_seq = []
        self.__word_tag_seq = []

        self.__chr_seq = []
        self.__chr_tag_seq = []
        self.__chr_space_seq = []

        self.__curr_bio = None
        self.__curr_tag = None
        self.__curr_attrs = None
        HTMLParser.reset(self)

    def handle_starttag(self, tag, attrs):
        if self.__curr_tag is None:
            self.__curr_bio = 'B'
            self.__curr_tag = tag
            self.__curr_attrs = attrs
        else:
            raise HTMLParseError('Error1', self.getpos())

    def handle_endtag(self, tag):
        if self.__curr_tag is not None and self.__curr_tag == tag:
            self.__curr_bio = None
            self.__curr_tag = None
            self.__curr_attrs = None
        else:
            raise HTMLParseError('Error2', self.getpos())

    def handle_data(self, data):
        if self.__chr_mode is True:
            tokens = data.strip()
        else:
            tokens = data.strip().split()

        for token in tokens:
            if self.__chr_mode is False or (self.__chr_mode is True and token != ' '):
                self.__word_seq.append(token)
                self.__word_tag_seq.append(
                    (self.__curr_bio, self.__curr_tag, self.__curr_attrs))

                chr_bio = self.__curr_bio

                if len(self.__chr_seq) == 0:
                    space_flag = False
                else:
                    space_flag = True

                for c in token:
                    self.__chr_seq.append(c)
                    self.__chr_tag_seq.append(
                        (chr_bio, self.__curr_tag, self.__curr_attrs))

                    if chr_bio == 'B':
                        chr_bio = 'I'

                    self.__chr_space_seq.append(space_flag)
                    space_flag = False

                if self.__curr_bio == 'B':
                    self.__curr_bio = 'I'

    def feed(self, data):
        HTMLParser.feed(self, data)
        if self.__curr_tag is not None:
            raise HTMLParseError('Error3', self.getpos())

    def get_word_seq(self):
        return self.__word_seq

    def get_word_tag_seq(self):
        return self.__word_tag_seq

    def get_chr_tag_seq(self):
        return self.__chr_tag_seq

    def get_chr_seq(self):
        return self.__chr_seq

    def get_chr_space_seq(self):
        return self.__chr_space_seq

    def set_chr_space_seq(self, seq):
        if len(seq) == len(self.__chr_seq):
            self.__chr_space_seq = seq
        else:
            raise

    def tokenize(self, chr_space_seq=None):
        if chr_space_seq is not None:
            self.set_chr_space_seq(chr_space_seq)

        self.__word_seq = []
        self.__word_tag_seq = []

        curr_word = ''
        curr_tag = (None, None, None)
        for c, space, tag in zip(
                self.__chr_seq, self.__chr_space_seq, self.__chr_tag_seq):
            if space:
                if len(curr_word) > 0:
                    self.__word_seq.append(curr_word)
                    self.__word_tag_seq.append(curr_tag)
                    curr_word = ''
                curr_tag = tag
            curr_word += c

        if len(curr_word) > 0:
            self.__word_seq.append(curr_word)
            self.__word_tag_seq.append(curr_tag)

        return self.__word_seq
