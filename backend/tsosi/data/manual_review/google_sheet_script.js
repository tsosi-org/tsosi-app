const rorBaseUrl = "https://api.ror.org/organizations/";
const rorIdRegex = new RegExp("^[a-zA-Z0-9]{9}$");

/**
 * @param {string} rorId the ROR ID.
 * @return The name of the ror record of the provided ID.
 * @customfunction
 */
function rorName(rorId) {
  if (!rorIdRegex.test(rorId)) {
    return null;
  }
  let url = rorBaseUrl + rorId;
  let response = UrlFetchApp.fetch(url);
  var json = response.getContentText();
  var data = JSON.parse(json);
  return data.name;
}

const wikidataBaseUrl = "https://www.wikidata.org/wiki/Special:EntityData/";
const wikidataIdRegex = new RegExp("^Q[0-9]+$");

/**
 * @param {string} wikidataId The Wikidata ID.
 * @return                    The English label of the wikidata record.
 * @customfunction 
 */
function wikidataName(wikidataId) {
  if (!wikidataIdRegex.test(wikidataId)) {
    return null;
  }
  let url = `${wikidataBaseUrl}${wikidataId}.json`;
  let response = UrlFetchApp.fetch(url);
  var json = response.getContentText();
  var data = JSON.parse(json);
  var entity = data.entities[wikidataId];
  if (entity.labels && entity.labels.en) {
    return entity.labels.en.value;
  }
  else if (entity.labels) {
    return entity.labels[Object.keys(entity.labels)[0]].value;
  }
  return null;
}

