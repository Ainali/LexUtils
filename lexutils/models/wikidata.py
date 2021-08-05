import logging
from enum import Enum
from typing import List, Dict

from wikibaseintegrator import wbi_core, wbi_datatype

# We get the URL for the Wikibase from here
import config
from wikibaseintegrator.wbi_functions import execute_sparql_query

from modules import wdqs


class WikimediaLanguageCode(Enum):
    DANISH = "da"
    SWEDISH = "sv"
    BOKMÅL = "nb"
    ENGLISH = "en"
    FRENCH = "fr"
    RUSSIAN = "ru"
    ESTONIAN = "et"
    MALAYALAM = "ml"
    LATIN = "la"
    HEBREW = "he"
    BASQUE = "eu"
    GERMAN = "de"
    BENGALI = "bn"
    CZECH = "cs"


class WikimediaLanguageQID(Enum):
    DANISH = "Q9035"
    SWEDISH = "Q9027"
    BOKMÅL = "Q25167"
    ENGLISH = "Q1860"
    FRENCH = "Q150"
    RUSSIAN = "Q7737"
    ESTONIAN = "Q9072"
    MALAYALAM = "Q36236"
    LATIN = "Q397"
    HEBREW = "Q9288"
    BASQUE = "Q8752"
    GERMAN = "Q188"
    BENGALI = "Q9610"
    CZECH = "Q9056"


class WikidataNamespaceLetters(Enum):
    PROPERTY = "P"
    ITEM = "Q"
    LEXEME = "L"


class EntityID:
    letter: WikidataNamespaceLetters
    number: int

    def __init__(self,
                 entity_id: str):
        if entity_id is not None:
            if len(entity_id) > 1:
                self.letter = WikidataNamespaceLetters[entity_id[0]]
                self.number = int(entity_id[1:])
            else:
                raise Exception("Entity ID was too short.")
        else:
            raise Exception("Entity ID was None")

    def to_string(self):
        return f"{self.letter}{self.number}"

    def extract_wdqs_json_entity_id(self, json: Dict, sparql_variable: str):
        self.__init__(json[sparql_variable]["value"].replace(
            config.wd_prefix, ""
        ))


class ForeignID:
    id: str
    property: str  # This is the property with type ExternalId
    source_item_id: str  # This is the Q-item for the source

    def __init__(self,
                 id: str = None,
                 property: str = None,
                 source_item_id: str = None):
        self.id = id
        self.property = EntityID(property).to_string()
        self.source_item_id = EntityID(source_item_id).to_string()


class Form:
    pass


class Sense:
    pass


class Lexeme:
    id: str
    lemma: str
    lexical_category: EntityID
    forms: List[Form]
    senses: List[Sense]

    def __init__(self,
                 id: str = None,
                 lemma: str = None,
                 lexical_category: str = None):
        self.id = EntityID(id).to_string()
        self.lemma = lemma
        self.lexical_category = EntityID(lexical_category)

    def parse_from_wdqs_json(self, json):
        self.forms = []
        self.senses = []
        for variable in json:
            logging.debug(variable)
            if variable == "form":
                form = Form(variable)
                self.forms.append(form)
            if variable == "sense":
                sense = Sense(variable)
                self.senses.append(sense)
            if variable == "category":
                self.lexical_category = EntityID(wdqs.extract_wikibase_value(variable))


    def url(self):
        return f"{config.wd_prefix}{self.id}"

    def upload_foreign_id_to_wikidata(self,
                                      foreign_id: ForeignID = None):
        """Upload to enrich the wonderful Wikidata <3"""
        logger = logging.getLogger(__name__)
        if foreign_id is None:
            raise Exception("Foreign id was None")
        print(f"Uploading {foreign_id.id} to {self.id}: {self.lemma}")
        statement = wbi_datatype.ExternalID(
            prop_nr=foreign_id.property,
            value=foreign_id.id,
        )
        described_by_source = wbi_datatype.ItemID(
            prop_nr="P1343",  # stated in
            value=foreign_id.source_item_id
        )
        # TODO does this overwrite or append?
        item = wbi_core.ItemEngine(
            data=[statement,
                  described_by_source],
            item_id=self.id
        )
        # debug WBI error
        # print(item.get_json_representation())
        result = item.write(
            config.login_instance,
            edit_summary=f"Added foreign identifier with [[{config.tool_url}]]"
        )
        logger.debug(f"result from WBI:{result}")
        print(self.url())
        # exit(0)

    def count_number_of_senses_with_P5137(self):
        """Returns an int"""
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?sense) as ?count)
        WHERE {{
          VALUES ?l {{wd:{self.id}}}.
          ?l ontolex:sense ?sense.
          ?sense skos:definition ?gloss.
          # Exclude lexemes without a linked QID from at least one sense
          ?sense wdt:P5137 [].
        }}'''))
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        return count

    def add_usage_example(
            document_id=None,
            sentence=None,
            lid=None,
            form_id=None,
            sense_id=None,
            word=None,
            publication_date=None,
            language_style=None,
            type_of_reference=None,
            source=None,
            line=None,
    ):
        # TODO convert to use OOP
        logger = logging.getLogger(__name__)
        # Use WikibaseIntegrator aka wbi to upload the changes in one edit
        link_to_form = wbi_datatype.Form(
            prop_nr="P5830",
            value=form_id,
            is_qualifier=True
        )
        link_to_sense = wbi_datatype.Sense(
            prop_nr="P6072",
            value=sense_id,
            is_qualifier=True
        )
        if language_style == "formal":
            style = "Q104597585"
        else:
            if language_style == "informal":
                style = "Q901711"
            else:
                print(_("Error. Language style {} ".format(language_style) +
                        "not one of (formal,informal). Please report a bug at " +
                        "https://github.com/egils-consulting/LexUtils/issues"))
                sleep(config.sleep_time)
                return "error"
        logging.debug("Generating qualifier language_style " +
                      f"with {style}")
        language_style_qualifier = wbi_datatype.ItemID(
            prop_nr="P6191",
            value=style,
            is_qualifier=True
        )
        # oral or written
        if type_of_reference == "written":
            medium = "Q47461344"
        else:
            if type_of_reference == "oral":
                medium = "Q52946"
            else:
                print(_("Error. Type of reference {} ".format(type_of_reference) +
                        "not one of (written,oral). Please report a bug at " +
                        "https://github.com/egils-consulting/LexUtils/issues"))
                sleep(config.sleep_time)
                return "error"
        logging.debug(_("Generating qualifier type of reference " +
                        "with {}".format(medium)))
        type_of_reference_qualifier = wbi_datatype.ItemID(
            prop_nr="P3865",
            value=medium,
            is_qualifier=True
        )
        if source == "riksdagen":
            if publication_date is not None:
                publication_date = datetime.fromisoformat(publication_date)
            else:
                print(_("Publication date of document {} ".format(document_id) +
                        "is missing. We have no fallback for that at the moment. " +
                        "Abort adding usage example."))
                return "error"
            stated_in = wbi_datatype.ItemID(
                prop_nr="P248",
                value="Q21592569",
                is_reference=True
            )
            # TODO lookup if we have a QID for the source
            document_id = wbi_datatype.ExternalID(
                prop_nr="P8433",  # Riksdagen Document ID
                value=document_id,
                is_reference=True
            )
            reference = [
                stated_in,
                document_id,
                wbi_datatype.Time(
                    prop_nr="P813",  # Fetched today
                    time=datetime.utcnow().replace(
                        tzinfo=timezone.utc
                    ).replace(
                        hour=0,
                        minute=0,
                        second=0,
                    ).strftime("+%Y-%m-%dT%H:%M:%SZ"),
                    is_reference=True,
                ),
                wbi_datatype.Time(
                    prop_nr="P577",  # Publication date
                    time=publication_date.strftime("+%Y-%m-%dT00:00:00Z"),
                    is_reference=True,
                ),
                type_of_reference_qualifier,
            ]
        elif source == "europarl":
            stated_in = wbi_datatype.ItemID(
                prop_nr="P248",
                value="Q5412081",
                is_reference=True
            )
            reference = [
                stated_in,
                wbi_datatype.Time(
                    prop_nr="P813",  # Fetched today
                    time=datetime.utcnow().replace(
                        tzinfo=timezone.utc
                    ).replace(
                        hour=0,
                        minute=0,
                        second=0,
                    ).strftime("+%Y-%m-%dT%H:%M:%SZ"),
                    is_reference=True,
                ),
                wbi_datatype.Time(
                    prop_nr="P577",  # Publication date
                    time="+2012-05-12T00:00:00Z",
                    is_reference=True,
                ),
                wbi_datatype.Url(
                    prop_nr="P854",  # reference url
                    value="http://www.statmt.org/europarl/v7/sv-en.tgz",
                    is_reference=True,
                ),
                # filename in archive
                wbi_datatype.String(
                    (f"europarl-v7.{config.language_code}" +
                     f"-en.{config.language_code}"),
                    "P7793",
                    is_reference=True,
                ),
                # line number
                wbi_datatype.String(
                    str(line),
                    "P7421",
                    is_reference=True,
                ),
                type_of_reference_qualifier,
            ]
        elif source == "ksamsok":
            # No date is provided unfortunately, so we set it to unknown value
            stated_in = wbi_datatype.ItemID(
                prop_nr="P248",
                value="Q7654799",
                is_reference=True
            )
            document_id = wbi_datatype.ExternalID(
                # K-Samsök URI
                prop_nr="P1260",
                value=document_id,
                is_reference=True
            )
            reference = [
                stated_in,
                document_id,
                wbi_datatype.Time(
                    prop_nr="P813",  # Fetched today
                    time=datetime.utcnow().replace(
                        tzinfo=timezone.utc
                    ).replace(
                        hour=0,
                        minute=0,
                        second=0,
                    ).strftime("+%Y-%m-%dT%H:%M:%SZ"),
                    is_reference=True,
                ),
                wbi_datatype.Time(
                    # We don't know the value of the publication dates unfortunately
                    prop_nr="P577",  # Publication date
                    time="",
                    snak_type="somevalue",
                    is_reference=True,
                ),
                type_of_reference_qualifier,
            ]
        else:
            raise ValueError(f"Did not recognize the source {source}")
        if reference is None:
            raise ValueError(_("No reference defined, cannot add usage example"))
        else:
            # This is the usage example statement
            claim = wbi_datatype.MonolingualText(
                sentence,
                "P5831",
                language=config.language_code,
                # Add qualifiers
                qualifiers=[
                    link_to_form,
                    link_to_sense,
                    language_style_qualifier,
                ],
                # Add reference
                references=[reference],
            )
            if config.debug_json:
                logging.debug(f"claim:{claim.get_json_representation()}")
            item = wbi_core.ItemEngine(
                item_id=lid,
            )
            # Updating appends by default in v0.11.0
            item.update(data=[claim])
            # if config.debug_json:
            #     print(item.get_json_representation())
            if config.login_instance is None:
                # Authenticate with WikibaseIntegrator
                print("Logging in with Wikibase Integrator")
                config.login_instance = wbi_login.Login(
                    user=config.username, pwd=config.password
                )
            result = item.write(
                config.login_instance,
                edit_summary=(
                    _("Added usage example " +
                      "with [[Wikidata:Tools/LexUtils]] v{}".format(config.version))
                )
            )
            if config.debug_json:
                logging.debug(f"result from WBI:{result}")
            # TODO add handling of result from WBI and return True == Success or False
            return result


class LexemeLanguage:
    lexemes: List[Lexeme]
    language_code: WikimediaLanguageCode
    language_qid: WikimediaLanguageQID
    senses_with_P5137_per_lexeme: float
    senses_with_P5137: int
    forms: int
    forms_with_an_example: int
    forms_without_an_example: int
    lexemes_count: int

    def __init__(self, language_code: str):
        self.language_code = WikimediaLanguageCode(language_code)
        self.language_qid = WikimediaLanguageQID[self.language_code.name]

    def fetch_forms_missing_an_example(self):
        results = execute_sparql_query(f'''
            #title:Forms that have no example demonstrating them
            select ?form ?lemma
            WHERE {{
              ?lexemeId dct:language wd:{self.language_qid.value};
                        wikibase:lemma ?lemma;
                        ontolex:lexicalForm ?form.
              MINUS {{
              ?lexemeId p:P5831 ?statement.
              ?statement ps:P5831 ?example;
                         pq:P6072 [];
                         pq:P5830 ?form_with_example.
              }}
            }}''')
        self.lexemes = []
        for lexeme_json in results:
            logging.debug(f"lexeme_json:{lexeme_json}")
            l = Lexeme.parse_from_wdqs_json(lexeme_json)
            self.lexemes.append(l)
        logging.info(f"Got {len(self.lexemes)} lexemes from WDQS for language {self.language_code.name}")


    def fetch_lexemes(self):
        # TODO port to use the Lexeme class instead of heavy dataframes which we don't need
        raise Exception("This is deprecated.")
        results = execute_sparql_query(f'''
        SELECT DISTINCT
        ?entity_lid ?form ?word (?categoryLabel as ?category) (?grammatical_featureLabel as ?feature) ?sense ?gloss
        WHERE {{
          ?entity_lid a ontolex:LexicalEntry; dct:language wd:{self.language_qid.value}.
          VALUES ?excluded {{
            # exclude affixes and interfix
            wd:Q62155 # affix
            wd:Q134830 # prefix
            wd:Q102047 # suffix
            wd:Q1153504 # interfix
          }}
          MINUS {{?entity_lid wdt:P31 ?excluded.}}
          ?entity_lid wikibase:lexicalCategory ?category.

          # We want only lexemes with both forms and at least one sense
          ?entity_lid ontolex:lexicalForm ?form.
          ?entity_lid ontolex:sense ?sense.

          # Exclude lexemes without a linked QID from at least one sense
          ?sense wdt:P5137 [].
          ?sense skos:definition ?gloss.
          # Get only the swedish gloss, exclude otherwise
          FILTER(LANG(?gloss) = "{self.language_code.value}")

          # This remove all lexemes with at least one example which is not
          # ideal
          MINUS {{?entity_lid wdt:P5831 ?example.}}
          ?form wikibase:grammaticalFeature ?grammatical_feature.
          # We extract the word of the form
          ?form ontolex:representation ?word.
          SERVICE wikibase:label
          {{ bd:serviceParam wikibase:language "{self.language_code.value},en". }}
        }}
        limit {config.sparql_results_size}
        offset {config.sparql_offset}
        ''')
        self.lexemes = []
        for lexeme_json in results:
            logging.debug(f"lexeme_json:{lexeme_json}")
            l = Lexeme.parse_wdqs_json(lexeme_json)
            self.lexemes.append(l)
        logging.info(f"Got {len(self.lexemes)} lexemes from WDQS for language {self.language_code.name}")

    def count_number_of_lexemes(self):
        """Returns an int"""
        logger = logging.getLogger(__name__)
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?l) as ?count)
        WHERE {{
          ?l dct:language wd:{self.language_qid.value}.
        }}'''))
        logger.debug(f"result:{result}")
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        return count

    def count_number_of_senses_with_p5137(self):
        """Returns an int"""
        logger = logging.getLogger(__name__)
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?sense) as ?count)
        WHERE {{
          ?l dct:language wd:{self.language_qid.value}.
          ?l ontolex:sense ?sense.
          ?sense skos:definition ?gloss.
          # Exclude lexemes without a linked QID from at least one sense
          ?sense wdt:P5137 [].
        }}'''))
        logger.debug(f"result:{result}")
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        return count

    def count_number_of_forms_without_an_example(self):
        """Returns an int"""
        # TODO fix this to count all senses in a given language
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?form) as ?count)
        WHERE {{
          ?l dct:language wd:{self.language_qid.value}.
          ?l ontolex:lexicalForm ?form.
          ?l ontolex:sense ?sense.
          # exclude lexemes that already have at least one example
          MINUS {{?l wdt:P5831 ?example.}}
          # Exclude lexemes without a linked QID from at least one sense
          ?sense wdt:P5137 [].
        }}'''))
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        self.forms_without_an_example = count

    def count_number_of_forms_with_examples(self):
        pass

    def count_number_of_forms(self):
        pass

    def calculate_statistics(self):
        self.lexemes_count: int = self.count_number_of_lexemes()
        self.senses_with_P5137: int = self.count_number_of_senses_with_p5137()
        self.calculate_senses_with_p5137_per_lexeme()

    def calculate_senses_with_p5137_per_lexeme(self):
        self.senses_with_P5137_per_lexeme = round(self.senses_with_P5137 / self.lexemes_count, 3)

    def print(self):
        print(f"{self.language_code.name} has "
              f"{self.senses_with_P5137} senses with linked QID in total on {self.lexemes_count} lexemes "
              f"which is {self.senses_with_P5137_per_lexeme} per lexeme.")


# TODO decide where to put this code
class LexemeStatistics:
    total_lexemes: int

    def __init__(self):
        self.calculate_total_lexemes()
        self.rank_languages_based_on_statistics()

    def calculate_total_lexemes(self) -> int:
        """Calculate how many lexemes exists in Wikidata"""
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?l) as ?count)
        WHERE {{
          ?l a ontolex:LexicalEntry.
        }}'''))
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        self.total_lexemes = count

    def rank_languages_based_on_statistics(self):
        logger = logging.getLogger(__name__)
        language_objects = []
        print("Fetching data...")
        for language_code in WikimediaLanguageCode:
            logger.info(f"Working on {language_code.name}")
            language = LexemeLanguage(language_code)
            language.calculate_statistics()
            language_objects.append(language)
        sorted_by_senses_with_p5137_per_lexeme = sorted(language_objects,
                                                        key=lambda language: language.senses_with_P5137_per_lexeme,
                                                        reverse=True)
        print("Languages ranked by most senses linked to items:")
        for language in sorted_by_senses_with_p5137_per_lexeme:
            language.print()
        # Generator expression
        total_lexemes_among_supported_languages: int = sum(language.lexemes_count for language in language_objects)
        # logger.debug(f"total:{total_lexemes_among_supported_languages}")
        percent = round(total_lexemes_among_supported_languages * 100 / self.total_lexemes)
        print(f"These languages have {total_lexemes_among_supported_languages} "
              f"lexemes out of {self.total_lexemes} in total ({percent}%)")
