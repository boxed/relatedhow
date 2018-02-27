module Main exposing (..)

import Dict exposing (Dict)
import Html exposing (Html, a, button, div, form, h1, input, text)
import Html.Attributes exposing (action, href, id, method, name, placeholder, title, type_, value)
import Html.Events exposing (onClick)
import Http
import Json.Decode


main =
    Html.program
        { init = init
        , view = view
        , update = update
        , subscriptions = subscriptions
        }


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


init : ( Model, Cmd Msg )
init =
    let
        model =
            Model files Dict.empty Nothing

        --            parseData (Model files Dict.empty) testData
    in
    ( model, loadNext model )


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


type alias Model =
    { filesLeft : List String
    , data : Dict Int Clade
    , error : Maybe Http.Error
    }



-- UPDATE


type Msg
    = FileLoaded (Result Http.Error String)


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

                ( Ok pk, Err _ ) ->
                    ( pk
                    , { name = name
                      , pk = pk
                      , parentPk = Nothing
                      }
                    )

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

        lines : List (List String)
        lines =
            List.map (String.split "\t") rawLines

        parsed : List ( Int, Clade )
        parsed =
            List.map parseLine lines
    in
    { model
        | data = Dict.union (Dict.fromList parsed) model.data
        , filesLeft = List.drop 1 model.filesLeft
    }


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        FileLoaded (Ok data) ->
            -- TODO: load next file
            ( parseData model data, Cmd.none )

        FileLoaded (Err (Http.BadStatus response)) ->
            -- TODO: load next file
            let
                cmd =
                    if List.isEmpty model.filesLeft then
                        Cmd.none
                    else
                        loadNext model
            in
            ( parseData model response.body, cmd )

        FileLoaded (Err error) ->
            ( { model | error = Just error }, Cmd.none )



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
        , form [ action "/", method "post" ]
            [ input
                [ id "q"
                , name "q"
                , placeholder "Comma separated list of species names, or just one species name"
                , title "Search"
                , type_ "text"
                , value ""
                ]
                []
            ]
        , text (toString (Dict.size model.data))
        , text (toString model.filesLeft)
        ]
