module Main exposing (..)

import Dict exposing (Dict)
import Html exposing (Html, a, button, div, form, h1, input, text)
import Html.Attributes exposing (action, href, id, method, name, placeholder, title, type_, value)
import Html.Events exposing (onClick, onInput)
import Http
import Json.Decode


main =
    Html.program
        { init = init
        , view = view
        , update = update
        , subscriptions = subscriptions
        }


type Msg
    = FileLoaded (Result Http.Error String)
    | Search
    | SearchText String


type alias Model =
    { filesLeft : List String
    , data : Dict Int Clade
    , error : Maybe Http.Error
    , searchText : String
    , selectedClade : Maybe Clade
    }


init : ( Model, Cmd Msg )
init =
    let
        model =
            Model files Dict.empty Nothing "171283" Nothing
    in
    ( model, loadNext model )


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        FileLoaded (Ok data) ->
            parseData model data ! [ Cmd.none ]

        FileLoaded (Err (Http.BadStatus response)) ->
            let
                cmd =
                    if List.isEmpty model.filesLeft then
                        Cmd.none
                    else
                        loadNext model
            in
            parseData model response.body ! [ cmd ]

        FileLoaded (Err error) ->
            { model | error = Just error } ! [ Cmd.none ]

        SearchText s ->
            { model | searchText = s } ! [ Cmd.none ]

        Search ->
            case String.toInt model.searchText of
                Ok pk ->
                    { model | selectedClade = Dict.get pk model.data } ! [ Cmd.none ]

                _ ->
                    model ! [ Cmd.none ]



--            model ! [ Cmd.none ]


files =
    [ "00_Biota.csv"
    , "01_Eukaryota.csv"
    , "02_Chromista.csv"
    , "03_superrosids.csv"
    , "04_superasterids.csv"
    , "05_Fungi.csv"
    , "06_Animalia.csv"
    , "07_Bilateria.csv"
    , "08_Deuterostomia.csv"
    , "09_Actinopterygii.csv"
    , "10_Reptilia.csv"
    , "11_Synapsidomorpha.csv"

    --    , "12_Protostomia.csv"
    ]


loadNext : Model -> Cmd Msg
loadNext model =
    case List.head model.filesLeft of
        Nothing ->
            Cmd.none

        Just nextFileName ->
            Http.send FileLoaded (Http.getString ("file:///Users/boxed/Projects/relatedhow/export_relevant/" ++ nextFileName))



-- MODEL


type alias Clade =
    { name : String
    , pk : Int
    , parentPk : Maybe Int
    }



-- UPDATE


parseLine : List String -> ( Int, Clade )
parseLine line =
    let
        first : Maybe String
        first =
            List.head line

        middle : Maybe String
        middle =
            List.head (List.drop 1 line)

        last : Maybe String
        last =
            List.head (List.drop 2 line)
    in
    case ( first, middle, last ) of
        ( Just pk, Just name, Just parentPk ) ->
            case ( String.toInt pk, String.toInt parentPk ) of
                ( Ok pk, Ok parentPk ) ->
                    ( pk
                    , { name = name
                      , pk = pk
                      , parentPk = Just parentPk
                      }
                    )

                ( Ok pk, Err e ) ->
                    if parentPk == "" then
                        ( pk
                        , { name = name
                          , pk = pk
                          , parentPk = Nothing
                          }
                        )
                    else
                        Debug.crash ("parseLine 3" ++ parentPk) parentPk

                ( _, _ ) ->
                    Debug.crash "parseLine 1"

        ( _, _, _ ) ->
            let
                foo =
                    Debug.log "asd" ( first, middle, last, line )
            in
            Debug.crash "parseLine 2"


parseData : Model -> String -> Model
parseData model data =
    let
        rawLines : List String
        rawLines =
            List.filter (\x -> not (String.isEmpty x)) (String.split "\n" data)

        trimmed : List String
        trimmed =
            List.map String.trim rawLines

        lines : List (List String)
        lines =
            List.map (String.split "\t") trimmed

        parsed : List ( Int, Clade )
        parsed =
            List.map parseLine lines
    in
    { model
        | data = Dict.union (Dict.fromList parsed) model.data
        , filesLeft = List.drop 1 model.filesLeft
    }



-- SUBSCRIPTIONS


subscriptions : Model -> Sub Msg
subscriptions model =
    Sub.none



-- VIEW


view : Model -> Html Msg
view model =
    div []
        [ h1 []
            [ a [ href "/" ]
                [ text "Related how?" ]
            ]
        , input
            [ id "q"
            , name "q"
            , placeholder "Comma separated list of species names, or just one species name"
            , title "Search"
            , type_ "text"
            , value model.searchText
            , onInput SearchText
            ]
            []
        , button [ onClick Search ] [ text "search" ]
        , text (toString (Dict.size model.data))
        , text (toString model.filesLeft)
        , text (toString model.selectedClade)
        ]
