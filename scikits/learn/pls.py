""" Partial Least Square
"""

# Author: Edouard Duchesnay <edouard.duchesnay@cea.fr>
# License: BSD Style.

from .base import BaseEstimator
#from scikits.learn.base import BaseEstimator
import warnings
import numpy as np
from scipy import linalg

def _nipals_twoblocks_inner_loop(X, Y, mode="A", max_iter = 500, tol = 1e-06):
    """Inner loop of the iterative NIPALS algorithm. provide an alternative
    of the svd(X'Y) ie. return the first left and rigth singular vectors of X'Y
    See PLS for the meaning of the parameters.
    """
    p = X.shape[1]
    q = Y.shape[1]
    y_score = Y[:,[0]]
    u_old = 0
    ite = 1
    # Inner loop of the Wold algo.
    while True:
        # Update u: the X weights
        # Mode A regress each X column on y_score
        u = np.dot(X.T, y_score)/np.dot(y_score.T, y_score)
        # Normalize u
        u /= np.sqrt(np.dot(u.T,u))
        
        # Update x_score: the X latent scores
        x_score    = np.dot(X, u)
        
        # Update v: the Y weights
        # Mode A regress each X column on y_score
        v = np.dot(Y.T, x_score)/np.dot(x_score.T, x_score)
        # Normalize v
        v /= np.sqrt(np.dot(v.T,v))
        
        # Update y_score: the Y latent scores
        y_score = np.dot(Y, v)
        
        u_diff = u - u_old
        if np.dot(u_diff.T, u_diff) < tol:
            break
        if ite == max_iter:
            warnings.warn('Maximum number of iterations reached')
            break
        u_old = u
        ite += 1
    return u, v

def _svd_cross_product(X, Y):
    C = np.dot(X.T,Y)
    U, s, Vh = linalg.svd(C, full_matrices = False)
    u = U[:,[0]]
    v = Vh.T[:,[0]]
    return u, v

def _scale_xy(X, Y, center_x, center_y, scale_x, scale_y):
    """ Scale/center (in place!) X, Y
    Return
    ------
        X, Y, x_mu, y_mu, x_std, y_std
    """
    x_mu  = y_mu  = 0
    x_std = x_std = 1
    if center_x:
        x_mu  = X.mean(axis=0)
        X -= x_mu 
    if scale_x :
        x_std = X.std(axis=0, ddof=1)
        X /= x_std
    if center_y:
        y_mu  = Y.mean(axis=0)
        Y -= y_mu 
    if scale_y:
        y_std = Y.std(axis=0, ddof=1)
        Y /= y_std
    return X, Y, x_mu, y_mu, x_std, y_std

class PLS(BaseEstimator):
    """Partial Least Square (PLS)

    We use the therminology defined by [Wegelin et al. 2000].
    This implementation uses the PLS Wold 2 blocks algorithm or NIPALS which is
    based on two nested loops: 
    (i) The outer loop iterate over compements. 
        (ii) The inner loop estimates the loading vectors. This can be done
        with two algo. (a) the inner loop of the original NIPALS algo or (b) a
        SVD on residuals cross-covariance matrices.
    
    This implementation can provide: 
    - PLS regression (PLS2) (PLS 2 blocks, mode A, with asymetric deflation)
    - PLS canonical (PLS 2 blocks, mode A, with symetric deflation)
    - CCA (PLS 2 blocks, mode B, with symetric deflation)

    Parameters
    ----------
    X: array-like of predictors, shape (n_samples, p)
        Training vectors, where n_samples in the number of samples and
        p is the number of predictors.

    Y: array-like of response, shape (n_samples, q)
        Training vectors, where n_samples in the number of samples and
        q is the number of response variables.

    n_components: int, number of components to keep. (default 2).

    deflation_mode: str, "canonical" or "regression". See notes.
        
    mode: "A" classical PLS and "B" CCA. See notes.
    
    center_x: boolean, center X? (default True)
    
    center_y: boolean, center Y? (default True)
        
    scale_x : boolean, scale X? (default True)
            
    scale_y : boolean, scale Y? (default True)
    
    algorithm: str "nipals" or "svd" the algorithm used to estimate the 
        weights, it will be called "n_components" time ie.: for each iteration
        of the outer loop.
    
    max_iter: an integer, the maximum number of iterations (default 500) of the
        NIPALS inner loop (used only if algorithm="nipals")
    
    tol: a not negative real, the tolerance used in the iterative algorithm
         default 1e-06.
 
    Attributes
    ----------
    x_weights_: array, [p x n_components] weights for the X block
    y_weights_: array, [q x n_components] weights for the Y block
    x_score_: array, [p x n_samples] scores for the X block
    y_score_: array, [q x n_samples] scores for the Y block

    Notes
    -----
    PLS mode A
        For each component k, find weights u, v that optimizes:
        max corr(Xk u, Yk v) * var(Xk u) var(Yk u) 
         |u| = |v| = 1
        max u'Xk' Yk v 
         |u| = |v| = 1
        
        Note that it maximizes both the correlations between the scores and the
        intra-block variances.
        
        With all deflation modes, the residual matrix of X (Xk+1) block is
        obtained by the deflation on the current X score: x_score.
    
        deflation_mode == "regression",the residual matrix of Y (Yk+1) block is 
            obtained by deflation on the current X score. This performs the PLS
            regression known as PLS2. This mode is prediction oriented.

        deflation_mode == "canonical",the residual matrix of Y (Yk+1) block is 
            obtained by deflation on the current Y score. This performs a
            canonical symetric version of the PLS regression. But slightly
            different than the CCA. This is mode mostly used for modeling

    PLS mode B, canonical, ie.: the CCA
        For each component k, find the weights u, v that maximizes
        max corr(Xk u, Yk v)
         |u| = |v| = 1
        max u'Xk' Yk v 
         |u| = |v| = 1

        Note that it maximizes only the correlations between the scores.

    References
    ----------
    Jacob A. Wegelin. A survey of Partial Least Squares (PLS) methods, with 
    emphasis on the two-block case. Technical Report 371, Department of 
    Statistics, University of Washington, Seattle, 2000.
    
    In french but still a reference:
    Tenenhaus, M. (1998). La regression PLS: theorie et pratique. Paris:
    Editions Technic.
    
    Examples
    --------
    >>> import numpy as np
    >>> from scikits.learn.pls import PLS
    >>> from scikits.learn.datasets import load_linnerud
    >>> d=load_linnerud()
    >>> X = d['data_exercise']
    >>> Y = d['data_physiological']
    
    >>> ## Canonical (symetric) PLS (PLS 2 blocks canonical mode A)
    >>> pls = PLS(deflation_mode="canonical")
    >>> pls.fit(X,Y, n_components=2)
    PLS(algorithm='nipals', deflation_mode='canonical', max_iter=500,
      center_x=True, center_y=True, n_components=2, tol=1e-06, scale_x=True,
      scale_y=True, mode='A')
    >>> print pls.x_weights_
    [[-0.58989155 -0.78900503]
     [-0.77134037  0.61351764]
     [ 0.23887653  0.03266757]]
    >>> print pls.y_weights_
    [[ 0.61330741 -0.25616063]
     [ 0.7469717  -0.11930623]
     [ 0.25668522  0.95924333]]
    >>> # check orthogonality of latent scores
    >>> print np.corrcoef(pls.x_scores_,rowvar=0)
    [[  1.00000000e+00   2.51221165e-17]
     [  2.51221165e-17   1.00000000e+00]]
    >>> print np.corrcoef(pls.y_scores_,rowvar=0)
    [[  1.00000000e+00  -8.57631722e-17]
     [ -8.57631722e-17   1.00000000e+00]]
     
    >>> ## Regression PLS (PLS 2 blocks regression mode A known as PLS2)
    >>> pls2 = PLS(deflation_mode="regression")
    >>> pls2.fit(X,Y, n_components=2)
    PLS(algorithm='nipals', deflation_mode='regression', max_iter=500,
      center_x=True, center_y=True, n_components=2, tol=1e-06, scale_x=True,
      scale_y=True, mode='A')

    See also
    --------
    PLS_SVD
    CCA

    """
    def __init__(self, n_components=2, deflation_mode = "canonical", mode = "A",
                 center_x = True, center_y = True,
                 scale_x  = True, scale_y  = True,
                 algorithm = "nipals",
                 max_iter = 500, tol = 1e-06):
        self.n_components = n_components
        self.deflation_mode = deflation_mode
        self.mode = mode
        self.center_x = center_x
        self.center_y = center_y
        self.scale_x  = scale_x
        self.scale_y  = scale_y
        self.algorithm = algorithm
        self.max_iter = max_iter
        self.tol      = tol
        self._DEBUG   = False

    def fit(self, X, Y,  **params):
        self._set_params(**params)
        # copy since this will contains the residuals (deflated) matrices
        X = np.asanyarray(X).copy()
        Y = np.asanyarray(Y).copy()

        n = X.shape[0]
        p = X.shape[1]
        q = Y.shape[1]

        if X.ndim != 2:
            raise ValueError('X must be a 2D array')

        if n != Y.shape[0]:
            raise ValueError(
                'Incompatible shapes: X has %s samples, while Y '
                'has %s' % (X.shape[0], Y.shape[0]))
        if self.n_components < 1 or self.n_components > p:
            raise ValueError('invalid number of components')
        if self.algorithm is "svd" and self.mode is "B":
            raise ValueError(
                'Incompatible configuration: mode B is not implemented with svd'
                'algorithm')
        if not self.deflation_mode in ["canonical","regression"]:
            raise ValueError(
                'The deflation mode is unknown')
        if self.mode is "B":
            raise ValueError('The mode B (CCA) is not implemented yet')
        # Scale (in place)
        X, Y, self.x_mu_, self.y_mu_, self.x_std_, self.y_std_\
            = _scale_xy(X, Y, self.center_x, self.center_y,\
                        self.scale_x, self.scale_y)
        # Residuals (deflated) matrices
        Xk = X
        Yk = Y
        # Results matrices
        self.x_scores_ = np.zeros((n, self.n_components))
        self.y_scores_ = np.zeros((n, self.n_components))
        self.x_weights_ = np.zeros((p, self.n_components))
        self.y_weights_ = np.zeros((q, self.n_components))
        # matrix of coefficients to be used internally by predict
        self.x_loadings_    = np.zeros((p, self.n_components))
        self.y_loadings_    = np.zeros((q, self.n_components))
            # x_regs_ contains, for each k, the regression of Xk on its score, 
            # ie.: Xk'x_scorek/x_scorek'x_scorek
            
        # NIPALS algo: outer loop, over components
        for k in xrange(self.n_components):
        
            #1) weights estimation (inner loop)
            # -----------------------------------
            if self.algorithm is "nipals":
                u, v = _nipals_twoblocks_inner_loop(
                        X=Xk, Y=Yk, mode=self.mode, 
                        max_iter=self.max_iter, tol=self.tol)
            if self.algorithm is "svd":
                u, v = _svd_cross_product(X=Xk, Y=Yk)
            # compute scores
            x_score = np.dot(Xk, u)
            y_score = np.dot(Yk, v)
            
            #2) Deflation (in place)
            # ----------------------
            # - regress Xk's on x_score
            x_loadings = np.dot(Xk.T, x_score)/np.dot(x_score.T, x_score) # p x 1
            # - substract rank-one approximations to obtain remainder matrix
            Xk -= np.dot(x_score, x_loadings.T)
            if self.deflation_mode is "canonical":
                # - regress Yk's on y_score, then substract rank-one approximation
                y_loadings  = np.dot(Yk.T, y_score)/np.dot(y_score.T, y_score) # q x 1
                Yk -= np.dot(y_score, y_loadings.T)
            if self.deflation_mode is "regression":
                # - regress Yk's on x_score, then substract rank-one approximation
                y_loadings  = np.dot(Yk.T, x_score)/np.dot(x_score.T, x_score) # q x 1
                Yk -= np.dot(x_score, y_loadings.T)
            
            # 3) Store weights and scores
            self.x_scores_[:,k] = x_score.ravel()
            self.y_scores_[:,k] = y_score.ravel()
            self.x_weights_[:,k] = u.ravel()
            self.y_weights_[:,k] = v.ravel()
            self.x_loadings_[:,k]= x_loadings.ravel()
            self.y_loadings_[:,k]= y_loadings.ravel()
            if self._DEBUG:
                print "component",k,"----------------------------------------------"
                print "X rank-one approximations and residual"
                print np.dot(x_score, x_loadings.T)
                print Xk
                print "Y rank-one approximations and residual"
                print np.dot(y_score, y_loadings.T)
                print Yk
        return self



class PLS_SVD(BaseEstimator):
    """Partial Least Square SVD
    
    Simply perform a svd on the crosscovariance matrix: X'Y
    The are no iterative deflation here.

    Parameters
    ----------
    X: array-like of predictors, shape (n_samples, p)
        Training vector, where n_samples in the number of samples and
        p is the number of predictors.

    Y: array-like of response, shape (n_samples, q)
        Training vector, where n_samples in the number of samples and
        q is the number of response variables.

    n_components: int, number of components to keep. (default 2).
    
    center_x: boolean, center X? (default True)
    
    center_y: boolean, center Y? (default True)
        
    scale_x: boolean, scale X? (default True)
            
    scale_y: boolean, scale Y? (default True)
     
    Attributes
    ----------
    x_weights_: array, [p x n_components] weights for the X block
    y_weights_: array, [q x n_components] weights for the Y block
    x_score_: array, [p x n_samples] scores for X the block
    y_score_: array, [q x n_samples] scores for the Y block

    Examples
    --------
    >>> import numpy as np
    >>> from scikits.learn.pls import PLS_SVD
    >>> pls_svd = PLS_SVD()
    >>> pls_svd.fit(X, Y)
    PLS_SVD(scale_x=True, scale_y=True, center_x=True, center_y=True,
        n_components=2)
    >>> print pls_svd.x_weights_
    [[-0.58989118 -0.77210756  0.23638594]
     [-0.77134059  0.45220001 -0.44782681]
     [ 0.23887675 -0.44650316 -0.86230669]]
    >>> print pls_svd.y_weights_
    [[ 0.61330742 -0.21404398  0.76028888]
     [ 0.7469717  -0.15563957 -0.64638193]
     [ 0.25668519  0.96434511  0.06442989]]
    >>> # note that on the first compements all PLS methods (PLS_SVD, PLS2, PLS 
    >>> # canonical) give the same results

    See also
    --------
    PLS
    CCA

    """
    def __init__(self, n_components=2,
                 center_x = True, center_y = True,
                 scale_x  = True, scale_y  = True):
        self.n_components = n_components
        self.center_x = center_x
        self.center_y = center_y
        self.scale_x  = scale_x
        self.scale_y  = scale_y
 
    def fit(self, X, Y,  **params):
        self._set_params(**params)
        X = np.asanyarray(X)
        y = np.asanyarray(Y)
        if self.center_x or self.scale_x: X = X.copy()
        if self.center_y or self.scale_y: Y = Y.copy()

        n = X.shape[0]
        p = X.shape[1]
        q = Y.shape[1]

        if X.ndim != 2:
            raise ValueError('X must be a 2D array')

        if n != Y.shape[0]:
            raise ValueError(
                'Incompatible shapes: X has %s samples, while Y '
                'has %s' % (X.shape[0], Y.shape[0]))

        if self.n_components < 1 or self.n_components > p:
            raise ValueError('invalid number of components')

        # Scale (in place)
        X, Y, self.x_mu_, self.y_mu_, self.x_std_, self.y_std_\
            = _scale_xy(X, Y, self.center_x, self.center_y,\
                        self.scale_x, self.scale_y)
        # svd(X'Y)
        C = np.dot(X.T,Y)
        U, s, V = linalg.svd(C, full_matrices = False)
        V = V.T
        self.x_score_    = np.dot(X, U)
        self.y_score_    = np.dot(Y, V)
        self.x_weights_ = U
        self.y_weights_ = V
        return self


