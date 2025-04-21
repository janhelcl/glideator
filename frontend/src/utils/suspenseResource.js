/**
 * Creates a resource that can be used with React Suspense
 * @param {Promise} promise - The promise to be wrapped
 * @returns {Object} A resource object with a read method that works with Suspense
 */
export function createResource(promise) {
  let status = 'pending';
  let result;
  let suspender = promise.then(
    data => {
      status = 'success';
      result = data;
    },
    error => {
      status = 'error';
      result = error;
    }
  );

  return {
    read() {
      if (status === 'pending') {
        throw suspender;
      } else if (status === 'error') {
        throw result;
      } else if (status === 'success') {
        return result;
      }
    }
  };
}

/**
 * Creates a prefetched resource for sites data
 * @param {Function} fetchFunction - The API function to fetch data
 * @returns {Object} A resource that can be read with Suspense
 */
export function createSitesResource(fetchFunction) {
  return createResource(fetchFunction());
} 