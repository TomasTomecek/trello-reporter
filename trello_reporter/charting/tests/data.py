"""
This file contains mock data for tests

names are fake, just in case, IDs are not -- should be all public data
"""

# this set of actions misses a move from board
faulty_move_to_board = """\
[{
  "data": {
    "list": {
      "id": "5125c3077f26e37d10008022",
      "name": "Next"
    },
    "board": {
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 566,
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "name": "card name"
    }
  },
  "idMemberCreator": "512553983f48177b52003710",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-10-24T20:58:06.672Z",
  "type": "createCard",
  "id": "544abd5e40f46cd41d74d089"
},
{
  "data": {
    "list": {
      "id": "5125c3077f26e37d10008022",
      "name": "Next"
    },
    "old": {
      "name": "card name"
    },
    "board": {
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 566,
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "name": "(3) card name"
    }
  },
  "idMemberCreator": "512553983f48177b52003710",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-10-24T21:00:39.151Z",
  "type": "updateCard",
  "id": "544abdf7de9097537ebe6143"
},
{
  "data": {
    "list": {
      "id": "5125c3077f26e37d10008022",
      "name": "Next"
    },
    "old": {
      "name": "(3) card name"
    },
    "board": {
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 566,
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "name": "(5) card name"
    }
  },
  "idMemberCreator": "512553983f48177b52003710",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-10-24T21:11:27.510Z",
  "type": "updateCard",
  "id": "544ac07f7d925c4bdd665191"
},
{
  "data": {
    "boardSource": {
      "id": "50fc6bb487602f214b003f71"
    },
    "list": {
      "id": "5277b65546e5ca917f00939e",
      "name": "New"
    },
    "board": {
      "shortLink": "wqe9UaaZ",
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 393,
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "name": "(5) card name"
    }
  },
  "idMemberCreator": "5126b85902bcecc94300206b",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-10-31T17:58:40.050Z",
  "type": "moveCardToBoard",
  "id": "5453cdd08086a4136bc5539d"
},
{
  "data": {
    "list": {
      "id": "5277b65546e5ca917f00939e",
      "name": "New"
    },
    "old": {
      "name": "(5) card name"
    },
    "board": {
      "shortLink": "wqe9UaaZ",
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 393,
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "name": "card name"
    }
  },
  "idMemberCreator": "5283c984d687c3743000d815",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-11-03T15:53:20.263Z",
  "type": "updateCard",
  "id": "5457a4f0ba4b3e51fc0b22f1"
},
{
  "data": {
    "listBefore": {
      "id": "5277b65546e5ca917f00939e",
      "name": "New"
    },
    "old": {
      "idList": "5277b65546e5ca917f00939e"
    },
    "board": {
      "shortLink": "wqe9UaaZ",
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 393,
      "idList": "5277b65546e5ca917f00939f",
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "name": "card name"
    },
    "listAfter": {
      "id": "5277b65546e5ca917f00939f",
      "name": "Backlog"
    }
  },
  "idMemberCreator": "5283c984d687c3743000d815",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-11-03T16:25:16.489Z",
  "type": "updateCard",
  "id": "5457ac6c98c45a5ee65f5b73"
},
{
  "data": {
    "listBefore": {
      "id": "5277b65546e5ca917f00939f",
      "name": "Backlog"
    },
    "old": {
      "idList": "5277b65546e5ca917f00939f"
    },
    "board": {
      "shortLink": "wqe9UaaZ",
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 393,
      "idList": "5277b65546e5ca917f0093a0",
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "name": "card name"
    },
    "listAfter": {
      "id": "5277b65546e5ca917f0093a0",
      "name": "Next"
    }
  },
  "idMemberCreator": "5283c984d687c3743000d815",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-11-13T21:28:53.778Z",
  "type": "updateCard",
  "id": "546522958921a0368f8b0499"
},
{
  "data": {
    "list": {
      "id": "5277b65546e5ca917f0093a0",
      "name": "Next"
    },
    "old": {
      "closed": false
    },
    "board": {
      "shortLink": "wqe9UaaZ",
      "id": "5277b65546e5ca917f00939d",
      "name": "board name"
    },
    "card": {
      "idShort": 393,
      "shortLink": "lSI9Mhvy",
      "id": "544abd5e40f46cd41d74d088",
      "closed": true,
      "name": "card name"
    }
  },
  "idMemberCreator": "5283c984d687c3743000d815",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2014-11-14T20:54:38.104Z",
  "type": "updateCard",
  "id": "54666c0e3e3f2aa396ddf450"
}]
"""

# these 2 actions did not save newer card name in database
undetected_name_change = """\
[{
  "data": {
    "cardSource": {
      "idShort": 547,
      "shortLink": "JbAFl3kV",
      "id": "57a9a7b40926fa6762fc07a6",
      "name": "Sprint 11"
    },
    "list": {
      "id": "56a90aa245f6f65409ac9639",
      "name": "In Progress"
    },
    "board": {
      "shortLink": "54yBmK8b",
      "id": "56a906e77b8507cf54ce9c15",
      "name": "board name"
    },
    "card": {
      "idShort": 600,
      "shortLink": "iNQpspWJ",
      "id": "57bc1a90b16af09d709ad712",
      "name": "Sprint 12"
    }
  },
  "idMemberCreator": "5717e6543ba22e304171bf49",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2016-08-23T09:42:41.406Z",
  "type": "copyCard",
  "id": "57bc1a91b16af09d709ad721"
},
{
  "data": {
    "list": {
      "id": "56a90aa245f6f65409ac9639",
      "name": "In Progress"
    },
    "old": {
      "name": "Sprint 12"
    },
    "board": {
      "shortLink": "54yBmK8b",
      "id": "56a906e77b8507cf54ce9c15",
      "name": "board name"
    },
    "card": {
      "idShort": 600,
      "shortLink": "iNQpspWJ",
      "id": "57bc1a90b16af09d709ad712",
      "name": "Sprint 13"
    }
  },
  "idMemberCreator": "5717e6543ba22e304171bf49",
  "memberCreator": {
    "username": "username",
    "fullName": "Full Name",
    "avatarHash": "74f0f80e56806ed68bfc460aa69c3f8e",
    "id": "512553983f48177b52003710",
    "initials": "FN"
  },
  "date": "2016-09-12T07:54:54.010Z",
  "type": "updateCard",
  "id": "57d65f4eaed4e1ab3e2c5c86"
}]
"""