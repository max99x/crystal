import nltk.corpus
import base


POPULAR_MALE_NAMES = [
  'wade', 'freddie', 'enrique', 'terrence', 'eduardo', 'rene', 'terrance',
  'kent', 'seth', 'tracy', 'marion', 'sergio', 'kirk', 'perry', 'salvador',
  'marshall', 'andy', 'virgil', 'ross', 'daryl', 'willard', 'clifton', 'morris',
  'isaac', 'julian', 'byron', 'sidney', 'johnnie', 'ivan', 'dave', 'alberto',
  'alfredo', 'casey', 'jaime', 'bob', 'ken', 'wallace', 'ian', 'jordan',
  'everett', 'jimmie', 'felix', 'armando', 'dwight', 'dwayne', 'max', 'hugh',
  'clayton', 'guy', 'nelson', 'allan', 'kurt', 'kelly', 'julio', 'cody',
  'lance', 'lonnie', 'darren', 'tyrone', 'mathew', 'ted', 'clinton', 'fernando',
  'javier', 'christian', 'jessie', 'neil', 'jamie', 'darryl', 'erik', 'claude',
  'cory', 'karl', 'adrian', 'jared', 'harvey', 'arnold', 'roland', 'mitchell',
  'ron', 'gabriel', 'brad', 'elmer', 'andre', 'franklin', 'duane', 'cecil',
  'chester', 'ben', 'raul', 'milton', 'edgar', 'leslie', 'rafael', 'nathaniel',
  'angel', 'brett', 'ruben', 'reginald', 'marc', 'gene', 'gilbert', 'tyler',
  'charlie', 'ramon', 'brent', 'lester', 'rick', 'sam', 'ricardo', 'shane',
  'hector', 'glen', 'clyde', 'roberto', 'vernon', 'maurice', 'herman', 'corey',
  'zachary', 'lewis', 'dan', 'derrick', 'pedro', 'dustin', 'jorge', 'greg',
  'dean', 'gordon', 'wesley', 'tim', 'alvin', 'leo', 'floyd', 'jerome',
  'darrell', 'warren', 'derek', 'leon', 'tommy', 'lloyd', 'bill', 'ronnie',
  'jon', 'alex', 'calvin', 'tom', 'jim', 'jay', 'oscar', 'miguel', 'clifford',
  'theodore', 'micheal', 'marcus', 'francisco', 'leroy', 'mario', 'bernard',
  'alexander', 'barry', 'randall', 'troy', 'ricky', 'eddie', 'don', 'edwin',
  'joel', 'ray', 'frederick', 'herbert', 'jesus', 'bradley', 'francis', 'kyle',
  'alfred', 'melvin', 'lee', 'jacob', 'chad', 'jeff', 'travis', 'jeffery',
  'glenn', 'vincent', 'marvin', 'allen', 'norman', 'curtis', 'rodney', 'manuel',
  'dale', 'nathan', 'leonard', 'stanley', 'mike', 'luis', 'tony', 'bryan',
  'danny', 'antonio', 'jimmy', 'earl', 'johnny', 'chris', 'philip', 'sean',
  'clarence', 'shawn', 'alan', 'craig', 'jesse', 'todd', 'phillip', 'ernest',
  'martin', 'victor', 'bobby', 'russell', 'carlos', 'eugene', 'howard', 'randy',
  'aaron', 'jeremy', 'louis', 'steve', 'billy', 'wayne', 'fred', 'harry',
  'adam', 'brandon', 'bruce', 'benjamin', 'roy', 'nicholas', 'lawrence',
  'ralph', 'willie', 'samuel', 'keith', 'gerald', 'terry', 'justin', 'jonathan',
  'albert', 'jack', 'juan', 'joe', 'roger', 'ryan', 'arthur', 'carl',
  'henry', 'douglas', 'harold', 'peter', 'patrick', 'walter', 'dennis',
  'jerry', 'joshua', 'gregory', 'raymond', 'andrew', 'stephen', 'eric',
  'scott', 'frank', 'jeffrey', 'larry', 'jose', 'timothy', 'gary', 'matthew',
  'jason', 'kevin', 'anthony', 'ronald', 'brian', 'edward', 'steven',
  'kenneth', 'george', 'donald', 'mark', 'paul', 'daniel', 'christopher',
  'thomas', 'joseph', 'charles', 'richard', 'david', 'william', 'michael',
  'robert', 'john', 'james'
]
POPULAR_FEMALE_NAMES = [
  'claire', 'katrina', 'erika', 'sherri', 'ramona', 'daisy', 'shelly', 'mae',
  'misty', 'toni', 'kristina', 'violet', 'bobbie', 'becky', 'velma', 'miriam',
  'sonia', 'felicia', 'jenny', 'leona', 'tracey', 'dianne', 'billie', 'olga',
  'brandy', 'carole', 'naomi', 'priscilla', 'kay', 'penny', 'leah', 'cassandra',
  'nina', 'margie', 'nora', 'jennie', 'gwendolyn', 'hilda', 'patsy', 'deanna',
  'christy', 'lena', 'myrtle', 'marsha', 'mabel', 'irma', 'maxine', 'terry',
  'mattie', 'vickie', 'jo', 'dora', 'caroline', 'stella', 'marian', 'courtney',
  'viola', 'lydia', 'glenda', 'heidi', 'marlene', 'minnie', 'nellie', 'tanya',
  'marcia', 'jackie', 'claudia', 'lillie', 'constance', 'georgia', 'joy',
  'tamara', 'allison', 'colleen', 'maureen', 'arlene', 'pearl', 'melinda',
  'delores', 'bessie', 'charlene', 'willie', 'vera', 'agnes', 'natalie',
  'jessie', 'kristin', 'gina', 'wilma', 'stacey', 'ella', 'tonya', 'lucy',
  'gertrude', 'terri', 'eileen', 'rosemary', 'tara', 'carla', 'vicki', 'jeanne',
  'beth', 'elsie', 'sue', 'alma', 'vanessa', 'kristen', 'katie', 'laurie',
  'jeanette', 'yolanda', 'loretta', 'melanie', 'brittany', 'holly', 'roberta',
  'vivian', 'ida', 'renee', 'ana', 'stacy', 'dana', 'marion', 'samantha',
  'june', 'annette', 'yvonne', 'audrey', 'bernice', 'dolores', 'beatrice',
  'erica', 'regina', 'sally', 'lynn', 'lorraine', 'joann', 'cathy', 'lauren',
  'geraldine', 'erin', 'jill', 'veronica', 'darlene', 'bertha', 'gail',
  'michele', 'suzanne', 'alicia', 'megan', 'danielle', 'valerie', 'eleanor',
  'joanne', 'jamie', 'lucille', 'clara', 'leslie', 'april', 'debbie', 'eva',
  'amber', 'hazel', 'rhonda', 'anita', 'juanita', 'emma', 'pauline', 'esther',
  'monica', 'charlotte', 'carrie', 'marjorie', 'elaine', 'ellen', 'ethel',
  'sheila', 'shannon', 'thelma', 'josephine', 'sylvia', 'sherry', 'kim',
  'edith', 'victoria', 'wendy', 'grace', 'cindy', 'rosa', 'carmen', 'tiffany',
  'edna', 'tracy', 'florence', 'connie', 'dawn', 'rita', 'gladys', 'crystal',
  'peggy', 'robin', 'emily', 'lillian', 'annie', 'diana', 'paula', 'norma',
  'phyllis', 'tina', 'lois', 'ruby', 'julia', 'bonnie', 'wanda', 'jacqueline',
  'anne', 'sara', 'louise', 'kathryn', 'andrea', 'marilyn', 'rachel', 'lori',
  'jane', 'irene', 'tammy', 'denise', 'beverly', 'theresa', 'kathy',
  'christina', 'judy', 'nicole', 'kelly', 'janice', 'rose', 'judith', 'ashley',
  'joan', 'katherine', 'mildred', 'cheryl', 'jean', 'evelyn', 'gloria', 'doris',
  'teresa', 'heather', 'julie', 'alice', 'diane', 'joyce', 'ann', 'frances',
  'catherine', 'janet', 'marie', 'christine', 'carolyn', 'stephanie', 'amanda',
  'debra', 'martha', 'pamela', 'kathleen', 'virginia', 'rebecca', 'anna', 'amy',
  'brenda', 'melissa', 'angela', 'cynthia', 'shirley', 'jessica', 'deborah',
  'kimberly', 'sarah', 'laura', 'michelle', 'sharon', 'ruth', 'carol', 'donna',
  'sandra', 'helen', 'betty', 'karen', 'nancy', 'lisa', 'dorothy', 'margaret',
  'susan', 'maria', 'jennifer', 'elizabeth', 'barbara', 'linda', 'patricia',
  'mary'
]


def WriteRules(outfile):
  names = ([('m', i.lower()) for i in nltk.corpus.names.read('male.txt')] +
           [('f', i.lower()) for i in nltk.corpus.names.read('female.txt')])
  for gender, name in names:
    ambiguity = Ambiguity(name, gender)
    name = base.LemmaToTerminals(name)
    outfile.write('PrpN[NUM=sg,SEX=%s,FRQ=%d] -> %s\n' %
                  (gender, -ambiguity, name))


def Ambiguity(name, gender):
  synsets = nltk.corpus.wordnet.synsets(name)
  sum = 0
  for synset in synsets:
    if synset.pos in (nltk.corpus.wordnet.ADJ, nltk.corpus.wordnet.ADJ_SAT):
      sum += 20
    elif not (synset.instance_hypernyms() and not synset.hypernyms()):
      sum += 1

  if gender == 'm' and name in POPULAR_MALE_NAMES:
    sum -= POPULAR_MALE_NAMES.index(name)
  elif gender == 'f' and name in POPULAR_FEMALE_NAMES:
    sum -= POPULAR_FEMALE_NAMES.index(name)

  return sum
